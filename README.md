## paraterra

`paraterra` is a CLI helper tool for managing `tfvars` files stored in parallel directories, and automating concurrent Terraform deploys using GitHub Actions Matrix strategy jobs. Paraterra parses Terraform plan output data and provides an aggregated, cross-environment view of changes and drift. 

### Use case  

Imagine you are on an AWS Cloud Platform team that needs to deploy cloud infrastructure defined by a single Terraform config to multiple accounts or Organization Units (groups of accounts) at once. Ideally these deployments would happen concurrently rather than sequentially, especially if you have dozens or hundreds of accounts. Additionally, you need a consolidated view into the changes that Terraform plans to make, so you can identify outlier plans without manually inspecting each plan output.  
  
The model for this type of functionality comes from AWS CloudFormation, which provides a feature called a StackSet which allows for deploying a single template concurrently to multiple accounts, with an accompaning web interface that allows you to search across all the accounts a StackSet targets to see deployment status. Terraform does not currently natively provide this feature.  
  
### Repo design and procedure assumptions  
The paraterra code makes certain assumptions about the structure of the repository it runs in:  
  
1) Each account has its own `tfvars` file that is used to parameterize the Terraform config. Parameterizing a single config with account specific `tfvars` files allows for granular, single account changes, as well as changes to groups of accounts, while at the same time version controlling variable values, and maintaining a single source of truth for the infrastructure definition.    
1) `tfvars` files are defined in `json` rather than `hcl` for ease of updating with common libraries  
1) Account level `tfvars` files are kept in a single directory in the project root called `accounts` with the following structure:  `accounts/{account-id}/{uuid}/terraform.tfvars.json`. The `uuid` subdirectory allows for multiple deployments of the same Terraform config to the same account, if necessary. Logical grouping of accounts - for example, by functional environment: dev, test, prod - is done by `tfvar` - for example, `environment: dev` - rather than with subdirectories. Grouping this way allows more flexibility with grouping and updating groupings.
1) Account specific Terraform backends are not kept in static files, but instead are generated during pipeline runs. Dynamic generation of the backend files allows for the underlying infrastructure providing the backend to change or be redeployed without having to update static backend files. Any backend is fine. 
  
### Pipelines  
`paraterra` can be used with any pipeline orchestrator that allows you to run jobs in parallel, and allows you to upload artifacts produced during those runs to a central repository, and download them all to a single job at at a later point. The pipeline example in this repo uses GitHub Actions.

The flow of the example pipeline:

1) the user kicks off the pipeline by running `terraform-update-matrix` via the GitHub Actions console or `gh` cli  
1) `terraform-update-matrix` calls `paraterra-compile-paths` to generate the list of tfvars files to update, based on input variables  
1) `terraform-update-matrix` calls `terraform-plan-upload` with a matrix strategy to run plans in parallel against the list of tfvars files from the previous job and uploads plan outputs to the artifacts store. 
1) Deploying human reviews aggregated plan output table, looking for outliers, and makes sure plans are as expected. If they are, deploying human manually approves the next job.
1) `terraform-update-matrix` calls `terraform-download-apply` with a matrix strategy to run in parallel over the list of plan output binaries. Each `terraform-download-apply` job downloads a plan output binary and applies it.
  
### Future Development Ideas
- Rewrite in Go to take advantage of Terraform Go SDK, so all terraform operations can be run from within the `paraterra` code base.  
- Add parsing, aggregation, and display of apply output.  
- Add commands for creating `paraterra` directory structure and `tfvars` files
- Add HTML generation of a visualization that can be opened in a web browser locally.  
- Create official reusable GHA actions utilizing `paraterra`