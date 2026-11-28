variable "subscription_id" {
  description = "ID de la suscripción de Azure (az account show --query id -o tsv)"
  type        = string
}

variable "location" {
  description = "Región de Azure"
  type        = string
  default     = "eastus2"
}

variable "resource_group_name" {
  type    = string
  default = "rg-toolia"
}

variable "dns_label" {
  description = "Nombre DNS único: <dns_label>.<region>.cloudapp.azure.com"
  type        = string
}

variable "vm_size" {
  description = "Tamaño de la VM. Para GPU usa una serie NC (requiere cuota y drivers NVIDIA)."
  type        = string
  default     = "Standard_D8s_v5"
}

variable "os_disk_size_gb" {
  type    = number
  default = 128
}

variable "admin_username" {
  type    = string
  default = "azureuser"
}

variable "ssh_public_key_path" {
  type    = string
  default = "~/.ssh/id_ed25519.pub"
}

variable "allowed_ssh_cidr" {
  description = "IP/CIDR desde donde se permite SSH, por ejemplo 190.1.2.3/32"
  type        = string
}

variable "repo_url" {
  description = "URL HTTPS del repositorio (si es privado, requiere token en la URL)"
  type        = string
  default     = "https://github.com/alexvirimi/ToolIA-Bot.git"
}

variable "repo_branch" {
  type    = string
  default = "chore-add-frontend"
}
