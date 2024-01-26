import click
from click_option_group import optgroup, RequiredMutuallyExclusiveOptionGroup
import tabulate
import os
import json
import sys
import csv
from typing import Dict, Set

class FiltersCommand(click.Command):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.params.insert(1, click.Option(('--filters',), help="Comma-delimited string of {tfvar_name}:{tfvar_value} to filter by (intersection)"))

# Custom type alias
MapOfMaps = Dict[str,Dict[str,str]]
MapOfSets = Dict[str,Set]

@click.group()
def cli():
    pass

def _split_filters(filters):
    return {split_filter[0]:split_filter[1]
            for each_filter in filters.split(',')
            for split_filter in each_filter.split(':')}

def _compile_paths(filters,exclude_accounts,shortened):
    accounts_path = 'accounts'
    tfvars_paths = []
    filters_dict = _split_filters(filters) if filters else {}

    for entry in os.scandir(accounts_path):
        if exclude_accounts and entry.path.split("/")[-1] in exclude_accounts:
            continue
        for path_with_region in os.scandir(entry.path):
            for path_with_region_and_uuid in os.scandir(path_with_region):
                tfvars_path = f'{path_with_region_and_uuid.path}'
                with open(f"{tfvars_path}/terraform.tfvars.json") as tfvars_file:
                    tfvars_dict = json.load(tfvars_file)
                    all_match = True
                    for key, value in filters_dict.items():
                        if tfvars_dict[key] != value:
                            all_match = False
                    if not all_match: 
                        continue
                    if shortened:
                        shortened_path = f"{'/'.join(tfvars_path.split('/')[4:])}"
                        tfvars_paths.append(shortened_path)
                    else:
                        tfvars_paths.append(tfvars_path)
    return tfvars_paths

def _get_accounts(filters):
    tfvars_paths = _compile_paths(filters=filters,
                                  exclude_accounts=None,
                                  shortened=True)
    return [path.split('/')[1] for path in tfvars_paths]

def _filter_and_map_accounts_to_full_paths(filters):
    tfvars_paths = _compile_paths(filters=filters,
                                  exclude_accounts=None,
                                  shortened=False)
    accounts_to_full_paths = {}
    for path in tfvars_paths:
        account = path.split('/')[5]
        accounts_to_full_paths[account] = f"{path}/terraform.tfvars.json"
    return accounts_to_full_paths

def _create_generated_file_path(account, file_name):
    generated_files_dir_path = os.path.join(os.path.dirname(__file__), 'generated_files', account)
    os.makedirs(generated_files_dir_path, exist_ok=True)
    generated_file_path = os.path.join(generated_files_dir_path, file_name)
    return generated_file_path

def _read_file(source_path,
               source_field_names,
               target_field_names,
               from_csv,
               from_json) -> MapOfMaps:
    with open(source_path) as file:
        if from_csv:
            reader = csv.DictReader(file)
        elif from_json:
            reader = json.load(file)
        accounts_to_fields_to_update = {}
        for row in reader:
            accounts_to_fields_to_update[row['account']] = {}
            for i, field_name in enumerate(source_field_names):
                accounts_to_fields_to_update[row['account']][field_name] = {}
                accounts_to_fields_to_update[row['account']][field_name]['value'] = row[field_name]
                if target_field_names:
                    accounts_to_fields_to_update[row['account']][field_name]['target_field_name'] = target_field_names[i]
    return accounts_to_fields_to_update

def _create_from_input(from_list, delete_fields, filters) -> MapOfMaps:
    accounts = _get_accounts(filters)
    accounts_to_fields_to_update = {}
    for account in accounts:
        if from_list:
            for item in from_list:
                field_name, value = item.split("=")
                accounts_to_fields_to_update[account] = {field_name:{'value':value}}
        elif delete_fields:
            for field_name in delete_fields:
                accounts_to_fields_to_update[account] = {field_name:{'delete':True}}
    return accounts_to_fields_to_update

@cli.command(cls=FiltersCommand, help="Prints list of paths to tfvars files")
@click.option("--exclude-accounts", required=False, default=None, help="Comma-delimited list of accounts to exclude")
@click.option("--shortened", is_flag=True, required=False, help="Returns shortened paths")
def paths(filters, exclude_accounts, shortened):
    exclude_accounts = exclude_accounts.split(",") if exclude_accounts else None
    tfvars_paths = _compile_paths(filters=filters,
                                  exclude_accounts=exclude_accounts,
                                  shortened=shortened)
    print(tfvars_paths)

@cli.command(cls=FiltersCommand,help='Prints list of account ids')
def accounts(filters):
    print(_get_accounts(filters))

@cli.command(cls=FiltersCommand, help="Updates tfvars files with \
             passed fields")
@optgroup.group('Source', cls=RequiredMutuallyExclusiveOptionGroup,
                help='Group description')
@optgroup.option('--from-csv', is_flag=True, help="Set to parse source as csv file")
@optgroup.option('--from-json', is_flag=True, help="Set to parse source as json file")
@optgroup.option('--from-list', help="Comma delimited list of field names and values \
                 to apply. Field names can be arbitrarily nested via delimiting names \
                 with colons: '{field_name1}={field_name1},{outer_field_name}:\
                 {inner_field_name}={field_value2}'")
@optgroup.option('--delete-fields', help="Deletes passed field names, of form comma \
              delimited list of arbitrarily nested field names, delimited by colon: \
              '{outer_field}:{inner_field},{other_field}'")
@click.option('--source-path', required=False, help="Path from current directory to source file")
@click.option('--source-field-names', required=False, help="Comma-delimited list of field names \
              in source to update")
@click.option('--target-field-names', required=False, help="Comma-delimited list (parallel to \
              --source-field-names) of field names in target to update, if different from \
              --source-field-names")
@click.option('--replace', is_flag=True, help="Updates actual tfvars files in place")
def update_tfvars(filters,
                  from_csv,
                  from_json,
                  from_list,
                  delete_fields,
                  source_path,
                  source_field_names,
                  target_field_names,
                  replace):
    source_field_names = source_field_names.split(',') if source_field_names else None
    target_field_names = target_field_names.split(',') if target_field_names else None
    from_list = from_list.split(',') if from_list else None
    delete_fields = delete_fields.split(":") if delete_fields else None

    if source_field_names and target_field_names:
        if len(source_field_names) != len(target_field_names):
            print("Error: --source-field-names and --target-field-names must be \
                  comma-delimited parallel lists of equal length")
            sys.exit(1)

    if (from_csv or from_json) and (not source_field_names or not source_path):
        print("Error: --source-field-names and --source-path is required when using \
              --from-csv or --from-json")
        sys.exit(1)

    accounts_to_full_paths = _filter_and_map_accounts_to_full_paths(filters)

    if from_csv or from_json:
        accounts_to_fields_to_update = _read_file(source_path=source_path,
                                                  from_csv=from_csv,
                                                  from_json=from_json, 
                                                  source_field_names=source_field_names, 
                                                  target_field_names=target_field_names)
    elif from_list or delete_fields:
        accounts_to_fields_to_update = _create_from_input(from_list=from_list, 
                                                          delete_fields=delete_fields, 
                                                          filters=filters)
    else:
        print("Error: must use one of --from-csv, --from-json, --from-list, or --delete-fields")
        sys.exit(1)
    
    _update_tfvars(accounts_to_full_paths=accounts_to_full_paths,
                   accounts_to_fields_to_update=accounts_to_fields_to_update,
                   replace=replace)   

def _update_tfvars(accounts_to_full_paths, accounts_to_fields_to_update, replace):
    for account, path in accounts_to_full_paths.items():
        with open(path) as tfvars_file:
            for field_name, field_details in accounts_to_fields_to_update[account].items():
                tfvars_dict = json.load(tfvars_file)
                if field_details.get('target_field_name'):
                    target_field_name = field_details.get('target_field_name')
                    if len(target_field_name.split(":")) > 1:
                        _update_nested_field(field_name_list=target_field_name.split(":"),
                                             field_details=field_details,
                                             tfvars_dict=tfvars_dict)
                    else:
                        _update_or_delete(field_name=field_details['target_field_name'],
                                          dict_location=tfvars_dict,
                                          field_details=field_details)    
                else:
                    if len(field_name.split(":")) > 1:
                        _update_nested_field(field_name_list=field_name.split(":"),
                                             field_details=field_details,
                                             tfvars_dict=tfvars_dict)
                    else:
                        _update_or_delete(field_name=field_name,
                                          dict_location=tfvars_dict,
                                          field_details=field_details)
        generated_file_path = _create_generated_file_path(account, "terraform.tfvars.json")
        with open(generated_file_path, "w", encoding='utf-8') as generated_updated_tfvars_file:
            json.dump(tfvars_dict, generated_updated_tfvars_file, indent=4)    
        if replace:
            with open(path, "w") as real_updated_tfvars_file:
                json.dump(tfvars_dict, real_updated_tfvars_file, indent=4) 

def _update_nested_field(field_name_list, field_details, tfvars_dict):
    nested_location = tfvars_dict
    final_item = field_name_list[-1]
    for target_field_name_next in field_name_list:
        if target_field_name_next == final_item:
            _update_or_delete(field_name=target_field_name_next,
                              field_details=field_details,
                              dict_location=nested_location)
        else:
            nested_location = nested_location[target_field_name_next]

def _update_or_delete(field_name, field_details, dict_location):
    if field_details.get('delete'):
        dict_location.pop(field_name)
    else:
        dict_location[field_name] = field_details['value']

@cli.command()
@click.option('--no-deletes', is_flag=True, required=False, help="Fails pipeline if changes include deletes")
@click.option('--no-creates', is_flag=True, required=False, help="Fails pipeline if changes include creates")
@click.option('--no-drift', is_flag=True, required=False, help="Fails pipeline if changes include drift")
@click.option('--allowed-props', required=False, help="Comma delimited list of properties that are allowed to have changes (in any resource)")
@click.option('--artifacts-path', required=True, help="Artifacts path for parsing")
def parse_plans(no_deletes,no_creates,no_drift,allowed_props,artifacts_path):
    valid = _parse_plans(no_deletes=no_deletes,
                 no_creates=no_creates,
                 no_drift=no_drift,
                 allowed_props=allowed_props,
                 artifacts_path=artifacts_path)
    
    if not valid:
        sys.exit(1)

def _parse_plans(no_deletes,no_creates,no_drift,allowed_props,artifacts_path):
    allowed_props = allowed_props.split(",") if allowed_props else None
    
    all_resource_change_counts, all_resource_drift_counts, all_resource_properties_changed = \
        _produce_counts(artifacts_path)
    
    return _validate_changes(no_creates=no_creates,
                      no_deletes=no_deletes,
                      no_drift=no_drift,
                      allowed_props=allowed_props,
                      all_resource_change_counts=all_resource_change_counts,
                      all_resource_drift_counts=all_resource_drift_counts,
                      all_resource_properties_changed=all_resource_properties_changed)
    
def _produce_counts(artifacts_path) -> (MapOfMaps, MapOfMaps, MapOfSets):
    resource_change_table = []
    resource_drift_table = []
    all_resource_change_counts = {}
    all_resource_drift_counts = {}
    all_resource_properties_changed = {}

    for plan_json in os.scandir(artifacts_path):
        resource_change_row = []
        resource_drift_row = []
        file_name = plan_json.path.split("/")[2]
        file_name_parts = file_name.split("+")
        account = file_name_parts[0]
        region = file_name_parts[1]
        uuid = file_name_parts[2]
        uuid = f"{uuid[:6]}..."
        
        resource_change_counts = {
            'no-op': 0,
            'create': 0,
            'read': 0,
            'update': 0,
            'delete-create': 0,
            'create-delete': 0,
            'delete': 0 
        }

        resource_properties_changed = set()

        resource_drift_counts = {
            'no-op': 0,
            'create': 0,
            'read': 0,
            'update': 0,
            'delete-create': 0,
            'create-delete': 0,
            'delete': 0 
        }
        with open(f"{plan_json.path}") as plan_file:
            plan_json = json.load(plan_file)
            if (resource_changes := plan_json.get("resource_changes")):
                for resource_change in resource_changes:
                    actions = resource_change.get("change").get("actions")
                    action = "-".join(actions)
                    resource_change_counts[action] += 1
                    _compare_before_and_after(resource_change, resource_properties_changed)
            if (resource_drifts := plan_json.get("resource_drift")):
                for resource_drift in resource_drifts:
                    actions = resource_drift.get("change").get("actions")
                    action = "-".join(actions)
                    resource_drift_counts[action] += 1
            resource_change_row = [account,region,uuid]
            resource_change_row.extend(list(resource_change_counts.values()))
            resource_change_table.append(resource_change_row)
        
            resource_drift_row = [account,region,uuid]
            resource_drift_row.extend(list(resource_drift_counts.values()))
            resource_drift_table.append(resource_drift_row)

            id = f"{account}:{region}:{uuid}"
            all_resource_change_counts[id] = resource_change_counts
            all_resource_drift_counts[id] = resource_drift_counts
            all_resource_properties_changed[id] = resource_properties_changed

    print("Resource Changes")
    print(tabulate.tabulate(resource_change_table, headers=["account","region","uuid","no-op","create","read","update","delete-create","create-delete","delete"], disable_numparse=True))
    print("\n")
    print("Resource Drift")
    print(tabulate.tabulate(resource_drift_table, headers=["account","region","uuid","no-op","create","read","update","delete-create","create-delete","delete"], disable_numparse=True))
    
    return (all_resource_change_counts, all_resource_drift_counts, all_resource_properties_changed)

def _compare_before_and_after(resource_change, resource_properties_changed):
    before = resource_change.get('change').get('before')
    after = resource_change.get('change').get('after')

    if before and after:
        for before_prop_name, before_prop_value in before.items():
            if before_prop_value != after.get(before_prop_name):
                resource_properties_changed.add(before_prop_name)

def _validate_changes(no_creates,
                      no_deletes,
                      no_drift,
                      allowed_props,
                      all_resource_change_counts,
                      all_resource_drift_counts,
                      all_resource_properties_changed):
    
    validation_failed = False

    if no_deletes:
        print("Checking for changes with deletes...")
        for id, counts in all_resource_change_counts.items():
            if counts['delete-create'] or \
                counts['create-delete'] or \
                counts['delete']:
                print(f"Error: Validation - {id} resource changes include deletes.")
                validation_failed = True
        else:
            print("No changes with deletes found!")
    
    if no_creates:
        print("Checking for changes with creates...")
        for id, counts in all_resource_change_counts.items():
            if counts['create'] or \
                counts['delete-create'] or \
                counts['create-delete']:
                print(f"Error: Validation - {id} - resource changes include creates.")
                validation_failed = True
        else:
            print("No changes with creates found!")
    
    if no_drift:
        print("Checking for drift...")
        fail_on_drift = False
        for id, counts in all_resource_drift_counts.items():
            for value in counts.values():
                if value:
                    print(f"Error: Validation - {id} - resources have drifted.")
                    validation_failed = True
                    fail_on_drift = True
        if not fail_on_drift:
            print("No drift found!")

    if allowed_props:
        print(f"Checking if prop changes are in {allowed_props}...")
        fail_on_allowed_props = False
        for id, changed_props in all_resource_properties_changed.items():
            for changed_prop in changed_props:
                if changed_prop not in allowed_props:
                    print(f"Error: Validation - {id} - resource property {changed_prop} not in allowed_props {allowed_props}")
                    validation_failed = True
                    fail_on_allowed_props = True
        if not fail_on_allowed_props:
            print(f"All props with changes allowed!")
            
    if validation_failed:
        print("Failing pipeline due to validation failure(s)...")
        return False
    else:
        return True

@cli.command()
@click.option("--artifacts-path", required=True, help="Path to artifact directory to scan")
def print_plan_files(artifacts_path):
    print([filename.path.split("/")[-1] for filename in os.scandir(artifacts_path)])

@cli.command(cls=FiltersCommand,help='Prints table of tfvars files with passed fields')
@click.option('--to-csv',is_flag=True,help='prints table in csv format')
def table(filters,to_csv):
    accounts_to_paths = _filter_and_map_accounts_to_full_paths(filters)
    table = []
    filters_dict = _split_filters(filters) if filters else {}
    filters_keys = list(filters_dict.keys())

    for account, path in accounts_to_paths.items():
        with open(path) as tfvars_file:
            tfvars_dict = json.load(tfvars_file)
            tfvars_values = [tfvars_dict[each_filter_key] 
                             for each_filter_key in filters_keys]
            row = [account] + tfvars_values
            table.append(row)
    
    headers = ["account"] + filters_keys
    if to_csv:
        headers = ','.join(headers)
        print(headers)
        for row in table:
            row = ','.join(row)
            print(row)
    else:        
        print(tabulate.tabulate(table, headers=headers, disable_numparse=True))
