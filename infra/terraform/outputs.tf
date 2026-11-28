output "public_ip" {
  value = azurerm_public_ip.pip.ip_address
}

output "url" {
  value = "https://${local.fqdn}"
}

output "ssh" {
  value = "ssh ${var.admin_username}@${azurerm_public_ip.pip.ip_address}"
}

output "copiar_datos" {
  description = "Ejecuta esto desde la raíz de tu repo local (Windows/PowerShell)"
  value       = "scp -r data/raw data/processed ${var.admin_username}@${azurerm_public_ip.pip.ip_address}:~/ToolIA-Bot/data/"
}
