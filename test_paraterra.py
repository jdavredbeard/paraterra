from paraterra import _parse_plans, _produce_counts

artifacts_path_1="ci-cd-test-data/terraform-plan-out-json"

def test_parse_plans_no_options():
    assert _parse_plans(no_deletes=None, 
                 no_creates=None, 
                 no_drift=None, 
                 allowed_props=None, 
                 artifacts_path=artifacts_path_1)

def test_parse_plans_no_create():
    assert _parse_plans(no_deletes=None,
                 no_creates=True,
                 no_drift=None,
                 allowed_props=None, 
                 artifacts_path=artifacts_path_1)

def test_parse_plans_no_delete():
    assert _parse_plans(no_deletes=True,
                 no_creates=None,
                 no_drift=None,
                 allowed_props=None,
                 artifacts_path=artifacts_path_1)

def test_parse_plans_no_drift_fails():
    assert not _parse_plans(no_deletes=None,
                 no_creates=None,
                 no_drift=True,
                 allowed_props=None,
                 artifacts_path=artifacts_path_1)

def test_parse_plans_no_deletes_creates_drift_fails():
    assert not _parse_plans(no_deletes=True,
                 no_creates=True,
                 no_drift=True,
                 allowed_props=None,
                 artifacts_path=artifacts_path_1)

def test_parse_plans_allowed_props_passes():
    assert _parse_plans(no_deletes=True,
                        no_creates=True,
                        no_drift=False,
                        allowed_props="tags,tags_all",
                        artifacts_path=artifacts_path_1)

def test_parse_plans_allowed_props_fails():
    assert not _parse_plans(no_deletes=True,
                        no_creates=True,
                        no_drift=False,
                        allowed_props="vpc",
                        artifacts_path=artifacts_path_1)

def test_resource_change_counts_are_accurate():
    all_resource_change_counts, _, _ = _produce_counts(artifacts_path_1)
    print(all_resource_change_counts)

    assert all_resource_change_counts.get("282837257756:us-east-1:345c91...").get("no-op") == 25
    assert all_resource_change_counts.get("282837257756:us-east-1:345c91...").get("create") == 0
    assert all_resource_change_counts.get("282837257756:us-east-1:345c91...").get("read") == 0
    assert all_resource_change_counts.get("282837257756:us-east-1:345c91...").get("update") == 0
    assert all_resource_change_counts.get("282837257756:us-east-1:345c91...").get("delete-create") == 0
    assert all_resource_change_counts.get("282837257756:us-east-1:345c91...").get("create-delete") == 0
    assert all_resource_change_counts.get("282837257756:us-east-1:345c91...").get("delete") == 0

    assert all_resource_change_counts.get("282837257756:us-east-1:53499e...").get("no-op") == 16
    assert all_resource_change_counts.get("282837257756:us-east-1:53499e...").get("create") == 0
    assert all_resource_change_counts.get("282837257756:us-east-1:53499e...").get("read") == 0
    assert all_resource_change_counts.get("282837257756:us-east-1:53499e...").get("update") == 9
    assert all_resource_change_counts.get("282837257756:us-east-1:53499e...").get("delete-create") == 0
    assert all_resource_change_counts.get("282837257756:us-east-1:53499e...").get("create-delete") == 0
    assert all_resource_change_counts.get("282837257756:us-east-1:53499e...").get("delete") == 0

def test_resource_drift_counts_are_accurate():
    _, all_resource_drift_counts, _ = _produce_counts(artifacts_path_1)
    print(all_resource_drift_counts)

    assert all_resource_drift_counts.get("282837257756:us-east-1:345c91...").get("no-op") == 0
    assert all_resource_drift_counts.get("282837257756:us-east-1:345c91...").get("create") == 0
    assert all_resource_drift_counts.get("282837257756:us-east-1:345c91...").get("read") == 0
    assert all_resource_drift_counts.get("282837257756:us-east-1:345c91...").get("update") == 1
    assert all_resource_drift_counts.get("282837257756:us-east-1:345c91...").get("delete-create") == 0
    assert all_resource_drift_counts.get("282837257756:us-east-1:345c91...").get("create-delete") == 0
    assert all_resource_drift_counts.get("282837257756:us-east-1:345c91...").get("delete") == 0

    assert all_resource_drift_counts.get("282837257756:us-east-1:53499e...").get("no-op") == 0
    assert all_resource_drift_counts.get("282837257756:us-east-1:53499e...").get("create") == 0
    assert all_resource_drift_counts.get("282837257756:us-east-1:53499e...").get("read") == 0
    assert all_resource_drift_counts.get("282837257756:us-east-1:53499e...").get("update") == 0
    assert all_resource_drift_counts.get("282837257756:us-east-1:53499e...").get("delete-create") == 0
    assert all_resource_drift_counts.get("282837257756:us-east-1:53499e...").get("create-delete") == 0
    assert all_resource_drift_counts.get("282837257756:us-east-1:53499e...").get("delete") == 0

def test_resource_properties_changed_counts_are_accurate():
    _, _, all_resource_properties_changed = _produce_counts(artifacts_path_1)
    print(all_resource_properties_changed)

    assert len(all_resource_properties_changed.get("282837257756:us-east-1:345c91...")) == 0
    
    assert len(all_resource_properties_changed.get("282837257756:us-east-1:53499e...")) == 2
    assert "tags" in all_resource_properties_changed.get("282837257756:us-east-1:53499e...")
    assert "tags_all" in all_resource_properties_changed.get("282837257756:us-east-1:53499e...")