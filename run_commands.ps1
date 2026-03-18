#!/usr/bin/env pwsh
<#
.SYNOPSIS
    AI Inbox Management System - Command Runner
    Provides quick access to common project commands

.DESCRIPTION
    Interactive menu for running essential project commands without memorizing syntax.
    Supports setup, services, debugging, and database operations.

.EXAMPLE
    .\run_commands.ps1
#>

param(
    [string]$Command = "",
    [switch]$Help
)

# Script configuration
$ProjectRoot = $PSScriptRoot
$VenvPath = Join-Path $ProjectRoot ".venv"
$UiPath = Join-Path $ProjectRoot "ui"

# Color configuration
$Colors = @{
    Info    = "Cyan"
    Success = "Green"
    Warning = "Yellow"
    Error   = "Red"
    Menu    = "Magenta"
}

function Write-Color {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

function Test-VenvActivated {
    return $null -ne $env:VIRTUAL_ENV
}

function Activate-Venv {
    $ActivateScript = Join-Path $VenvPath "Scripts\Activate.ps1"
    if (Test-Path $ActivateScript) {
        & $ActivateScript
        Write-Color "✓ Virtual environment activated" $Colors.Success
    }
    else {
        Write-Color "✗ Virtual environment not found at $VenvPath" $Colors.Error
        exit 1
    }
}

function Show-Menu {
    Write-Color "`n=== AI Inbox Management System - Command Runner ===" $Colors.Menu
    Write-Color "1. Setup & Installation" $Colors.Info
    Write-Color "  1.1  Create virtual environment" $Colors.Info
    Write-Color "  1.2  Activate virtual environment" $Colors.Info
    Write-Color "  1.3  Install dependencies" $Colors.Info
    Write-Color "  1.4  Initialize database" $Colors.Info
    Write-Color ""
    Write-Color "2. Start Services" $Colors.Info
    Write-Color "  2.1  Start Redis (Docker)" $Colors.Info
    Write-Color "  2.2  Stop Redis" $Colors.Info
    Write-Color "  2.3  Start Celery worker with beat" $Colors.Info
    Write-Color "  2.4  Start MCP server (port 9000)" $Colors.Info
    Write-Color "  2.5  Start main polling loop" $Colors.Info
    Write-Color ""
    Write-Color "3. Frontend (UI)" $Colors.Info
    Write-Color "  3.1  Install UI dependencies" $Colors.Info
    Write-Color "  3.2  Start dev server (Vite)" $Colors.Info
    Write-Color "  3.3  Build for production" $Colors.Info
    Write-Color ""
    Write-Color "4. Testing & Debugging" $Colors.Info
    Write-Color "  4.1  Run full pipeline debug" $Colors.Info
    Write-Color "  4.2  Debug orchestrator" $Colors.Info
    Write-Color "  4.3  Debug polling loop" $Colors.Info
    Write-Color "  4.4  Debug label system" $Colors.Info
    Write-Color "  4.5  Test Supabase connection" $Colors.Info
    Write-Color "  4.6  Test label system" $Colors.Info
    Write-Color "  4.7  Test unknown tenant routing" $Colors.Info
    Write-Color ""
    Write-Color "5. Monitoring" $Colors.Info
    Write-Color "  5.1  Check Celery scheduled tasks" $Colors.Info
    Write-Color "  5.2  Check active Celery tasks" $Colors.Info
    Write-Color "  5.3  Check Celery stats" $Colors.Info
    Write-Color "  5.4  Redis connection test" $Colors.Info
    Write-Color ""
    Write-Color "6. Deployment" $Colors.Info
    Write-Color "  6.1  Deploy with validation" $Colors.Info
    Write-Color "  6.2  Patch MCP server" $Colors.Info
    Write-Color "  6.3  Patch email tools" $Colors.Info
    Write-Color ""
    Write-Color "9. Show help" $Colors.Info
    Write-Color "0. Exit" $Colors.Info
    Write-Color ""
}

function Execute-Command {
    param([string]$Choice)

    Set-Location $ProjectRoot

    switch ($Choice) {
        # Setup
        "1.1" {
            Write-Color "Creating virtual environment..." $Colors.Warning
            python -m venv .venv
            Write-Color "✓ Virtual environment created" $Colors.Success
        }
        "1.2" {
            Activate-Venv
        }
        "1.3" {
            Write-Color "Installing dependencies..." $Colors.Warning
            pip install -r requirements.txt
            Write-Color "✓ Dependencies installed" $Colors.Success
        }
        "1.4" {
            Write-Color "Initializing database..." $Colors.Warning
            python init_db.py
            Write-Color "✓ Database initialized" $Colors.Success
        }

        # Services
        "2.1" {
            Write-Color "Starting Redis (Docker)..." $Colors.Warning
            docker-compose up -d
            Write-Color "✓ Redis started" $Colors.Success
        }
        "2.2" {
            Write-Color "Stopping Redis..." $Colors.Warning
            docker-compose down
            Write-Color "✓ Redis stopped" $Colors.Success
        }
        "2.3" {
            if (-not (Test-VenvActivated)) { Activate-Venv }
            Write-Color "Starting Celery worker with beat..." $Colors.Warning
            celery -A main.celery_app worker -B -l info
        }
        "2.4" {
            if (-not (Test-VenvActivated)) { Activate-Venv }
            Write-Color "Starting MCP server on port 9000..." $Colors.Warning
            python run_mcp_server.py
        }
        "2.5" {
            if (-not (Test-VenvActivated)) { Activate-Venv }
            Write-Color "Starting main polling loop..." $Colors.Warning
            python main.py
        }

        # UI
        "3.1" {
            Write-Color "Installing UI dependencies..." $Colors.Warning
            Set-Location $UiPath
            npm install
            Write-Color "✓ UI dependencies installed" $Colors.Success
            Set-Location $ProjectRoot
        }
        "3.2" {
            Write-Color "Starting Vite dev server..." $Colors.Warning
            Set-Location $UiPath
            npm run dev
            Set-Location $ProjectRoot
        }
        "3.3" {
            Write-Color "Building for production..." $Colors.Warning
            Set-Location $UiPath
            npm run build
            Write-Color "✓ Build complete" $Colors.Success
            Set-Location $ProjectRoot
        }

        # Testing & Debugging
        "4.1" {
            if (-not (Test-VenvActivated)) { Activate-Venv }
            Write-Color "Running full pipeline debug..." $Colors.Warning
            python debug_full_pipeline.py
        }
        "4.2" {
            if (-not (Test-VenvActivated)) { Activate-Venv }
            Write-Color "Running orchestrator debug..." $Colors.Warning
            python debug_orchestrator_pipeline.py
        }
        "4.3" {
            if (-not (Test-VenvActivated)) { Activate-Venv }
            Write-Color "Running polling loop debug..." $Colors.Warning
            python debug_polling_loop.py
        }
        "4.4" {
            if (-not (Test-VenvActivated)) { Activate-Venv }
            Write-Color "Running label system debug..." $Colors.Warning
            python debug_labels.py
        }
        "4.5" {
            if (-not (Test-VenvActivated)) { Activate-Venv }
            Write-Color "Testing Supabase connection..." $Colors.Warning
            python test_supabase.py
        }
        "4.6" {
            if (-not (Test-VenvActivated)) { Activate-Venv }
            Write-Color "Testing label system..." $Colors.Warning
            python test_label_system.py
        }
        "4.7" {
            if (-not (Test-VenvActivated)) { Activate-Venv }
            Write-Color "Testing unknown tenant routing..." $Colors.Warning
            python test_unknown_tenant.py
        }

        # Monitoring
        "5.1" {
            if (-not (Test-VenvActivated)) { Activate-Venv }
            Write-Color "Checking Celery scheduled tasks..." $Colors.Warning
            celery -A main.celery_app inspect scheduled
        }
        "5.2" {
            if (-not (Test-VenvActivated)) { Activate-Venv }
            Write-Color "Checking active Celery tasks..." $Colors.Warning
            celery -A main.celery_app inspect active
        }
        "5.3" {
            if (-not (Test-VenvActivated)) { Activate-Venv }
            Write-Color "Checking Celery stats..." $Colors.Warning
            celery -A main.celery_app inspect stats
        }
        "5.4" {
            Write-Color "Testing Redis connection..." $Colors.Warning
            redis-cli ping
        }

        # Deployment
        "6.1" {
            if (-not (Test-VenvActivated)) { Activate-Venv }
            Write-Color "Deploying with validation..." $Colors.Warning
            python fixdeploy.py
        }
        "6.2" {
            if (-not (Test-VenvActivated)) { Activate-Venv }
            Write-Color "Patching MCP server..." $Colors.Warning
            python patch_mcp_server.py
        }
        "6.3" {
            if (-not (Test-VenvActivated)) { Activate-Venv }
            Write-Color "Patching email tools..." $Colors.Warning
            python patch_tools_email.py
        }

        # Help
        "9" {
            Show-Help
        }

        # Exit
        "0" {
            Write-Color "Exiting..." $Colors.Info
            exit 0
        }

        default {
            Write-Color "✗ Invalid choice. Please try again." $Colors.Error
        }
    }
}

function Show-Help {
    Write-Color @"
AI Inbox Management System - Command Runner

USAGE:
    .\run_commands.ps1 [Command] [Options]

EXAMPLES:
    .\run_commands.ps1                    # Show interactive menu
    .\run_commands.ps1 -Help              # Show this help
    .\run_commands.ps1 -Command 1.1       # Create venv directly

COMMANDS:
    Setup & Installation:
        1.1  Create virtual environment
        1.2  Activate virtual environment
        1.3  Install dependencies
        1.4  Initialize database

    Services:
        2.1  Start Redis
        2.2  Stop Redis
        2.3  Start Celery worker
        2.4  Start MCP server
        2.5  Start polling loop

    UI:
        3.1  Install UI dependencies
        3.2  Start dev server
        3.3  Build for production

    Testing:
        4.1-4.7  Various debug and test commands

    Monitoring:
        5.1-5.4  Celery and Redis monitoring

    Deployment:
        6.1-6.3  Deployment and patching tools

For full documentation, see COMMANDS.md in the project root.
"@ $Colors.Info
}

# Main execution
if ($Help) {
    Show-Help
    exit 0
}

if ($Command) {
    Execute-Command $Command
    exit $LASTEXITCODE
}

# Interactive mode
while ($true) {
    Show-Menu
    $Choice = Read-Host "Enter your choice"
    Write-Color ""
    
    if ($Choice -eq "0") {
        break
    }
    
    Execute-Command $Choice
    
    if ($Choice -in @("2.3", "2.4", "2.5", "3.2")) {
        Write-Color "`nPress any key to return to menu..."
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    }
}

Write-Color "`n✓ Command runner closed" $Colors.Success
