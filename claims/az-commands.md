az group list // resource group
az group list --query "[].name" -o tsv // all names of resource groups in plain text (no json)
