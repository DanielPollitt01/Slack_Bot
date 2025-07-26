param(
    [Parameter(Mandatory=$true)]
    [string]$message
)

# Add all changes
git add .

# Commit with the provided message
git commit -m $message

# Push to GitHub
git push

Write-Host "Changes committed and pushed successfully!" -ForegroundColor Green 