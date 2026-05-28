$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot
$ip = (Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
        $_.IPAddress -notlike "127.*" -and
        $_.IPAddress -notlike "169.254.*" -and
        $_.InterfaceAlias -notlike "*Loopback*" -and
        $_.InterfaceAlias -notlike "*vEthernet*" -and
        $_.InterfaceAlias -notlike "*Virtual*" -and
        $_.InterfaceAlias -notlike "*VMware*" -and
        $_.InterfaceAlias -notlike "*VirtualBox*" -and
        $_.InterfaceAlias -notlike "*Docker*"
    } |
    Select-Object -First 1 -ExpandProperty IPAddress)

Write-Host "Local access:   http://localhost:8501"
if ($ip) {
    Write-Host "Network access: http://$($ip):8501"
    Write-Host "Use the network URL from another device on the same Wi-Fi/LAN."
} else {
    Write-Host "Could not detect a LAN IP address."
}

python -m streamlit run app_pdf_mvp.py --server.address 0.0.0.0 --server.port 8501 --server.headless true
