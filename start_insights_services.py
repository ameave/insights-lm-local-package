#!/usr/bin/env python3
"""
start_insights_services.py

This script pulls the latest Docker images and starts the local AI services
and Supabase services using Docker Compose. It also handles environment setup
and configuration for SearXNG.

Usage:
    python start_insights_services.py [...options]

Options:
    --profile [cpu|gpu-nvidia|gpu-amd|none] : Specify the Docker Compose profile to use (default: none).
    --environment [private|public]          : Specify the environment configuration to use (default: private).
    --supabase-only                         : Only start the Supabase services and exit.
    --start                                 : Don't stop existing containers before starting new ones.
    --extra-compose-files [files...]        : Additional Docker Compose files to include when starting Supabase.
"""

import os
import subprocess
import shutil
import argparse
import secrets

def run_command(cmd, cwd=None, capture_output=False):
    """Run a shell command and print it."""
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=cwd, check=True, capture_output=capture_output, text=True)
    return result


def prepare_env():
    """Copy .env to insights-lm-local-package and local-supabase"""
    env_path = ".env"

    secrets_path = ".secrets"
    if not os.path.exists(secrets_path):
        os.mkdir(secrets_path)

    print(f"Preparing secrets in {secrets_path}...")

    # Empty the .secrets directory
    for filename in os.listdir(secrets_path):
        file_path = os.path.join(secrets_path, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)

    with open(env_path, 'r') as file:
        content = file.read()
        # Remove comments and empty lines
        lines = [line for line in content.splitlines() if line.strip() and not line.strip().startswith('#')]
        secret_keys = ["KEY", "PASSWORD", "USERNAME", "SALT", "TOKEN", "SECRET", "AUTH"]

        for line in lines:
            if not any(key in line for key in secret_keys):
                continue

            key, value = line.split('=', 1)
            key = key.lower()
            value = value.strip().strip('"').strip("'")

            secret_file_path = os.path.join(secrets_path, key)
            with open(secret_file_path, 'w') as secret_file:
                secret_file.write(value)

        print("Secrets prepared.")


def stop_existing_containers(project=None, profile=None):
    """Stop and remove existing containers for the unified project 'insights-lm'."""
    print("Stopping and removing existing containers for the unified project 'insights-lm'...")
    cmd = docker_compose(profile=profile)
    cmd.extend(["down"])
    run_command(cmd)


def pull_docker_images(compose_files=[], update=False):
    """Pull the latest Docker images for the given compose files."""
    chkcmd = ["docker", "image", "ls", "ollama/ollama:latest"]
    container_check = subprocess.run(chkcmd, check=True, capture_output=True, text=True)
    
    if "ollama/ollama:latest" in container_check.stdout and not update:
        print("Images already present, skipping pull.")
        return

    """Pull the latest Docker images for the given compose files."""
    for compose_file in compose_files:
        print(f"Pulling latest images for {compose_file}...")
        cmd = ["docker", "compose", "-p", "insights-lm", "--env-file", ".env", "-f", compose_file, "pull"]
        run_command(cmd)


def docker_compose(project=None, profile=None, environment=None, compose_files=[], env_file=".env"):
    """Construct the docker-compose command with the given parameters."""

    cmd = ["docker", "compose"]
    if project is not None:
        cmd.extend(["-p", project])
    
    cmd.extend(["--env-file", env_file])
    
    if profile and profile != "None":
        cmd.extend(["--profile", profile])

    cmd.extend(["-f", "docker-compose.yml", "-f", "docker-compose.override.yml"])

    if environment:
        environment_compose = os.path.join("local-ai-packaged", f"docker-compose.override.{environment}.yml")
        cmd.extend(["-f", environment_compose])

    for file in compose_files:
        if os.path.exists(file):
            cmd.extend(["-f", file])
        else:
            print(f"Warning: Docker Compose file {file} does not exist and will be skipped.")

    return cmd


def generate_yml(project=None, profile=None, environment=None, compose_files=[]):
    """Generate the combined docker-compose.yml content."""
    print("Generating combined docker-compose.yml...")

    cmd = docker_compose(project, profile, environment, compose_files)

    cmd.append("config")

    result = run_command(cmd, capture_output=True)

    return result.stdout


def start_insights_lm(project=None, profile=None, environment=None, compose_files=[]):
    """Start the Insights LM services."""
    print("Starting Insights LM services...")
    
    cmd = docker_compose(project, profile, environment, compose_files)
    
    cmd.extend(["up", "-d"])

    run_command(cmd)


def generate_searxng_secret_key():
    """Generate a secret key for SearXNG based on the current platform."""
    print("Checking SearXNG settings...")

    settings_path = os.path.join("searxng", "settings.yml")
    settings_base_path = os.path.join("searxng", "settings-base.yml")

    if not os.path.exists(settings_base_path):
        print(f"Warning: SearXNG base settings file not found at {settings_base_path}")
        return

    if not os.path.exists(settings_path):
        print(f"SearXNG settings.yml not found. Creating from {settings_base_path}...")
        try:
            shutil.copyfile(settings_base_path, settings_path)
            print(f"Created {settings_path} from {settings_base_path}")
        except Exception as e:
            print(f"Error creating settings.yml: {e}")
            return

    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            content = f.read()

        if "ultrasecretkey" not in content:
            print("SearXNG secret key already set in settings.yml, no action needed.")
            return

        # Use Python's secure random generator; cross-platform and avoids subprocesses
        
        random_key = secrets.token_hex(32)
        new_content = content.replace("ultrasecretkey", random_key)

        with open(settings_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        print("SearXNG secret key generated successfully.")

    except Exception as e:
        print(f"Error generating SearXNG secret key: {e}")



def check_and_fix_docker_compose_for_searxng():
    """Check and modify docker-compose.yml for SearXNG first run."""
    docker_compose_path = "docker-compose.yml"
    if not os.path.exists(docker_compose_path):
        print(f"Warning: Docker Compose file not found at {docker_compose_path}")
        return
    try:
        # Read docker-compose.yml
        with open(docker_compose_path, 'r', encoding='utf-8') as file:
            content = file.read()

        # Simplified first-run detection: check settings.yml for the placeholder
        settings_path = os.path.join('searxng', 'settings.yml')
        placeholder_present = False
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r', encoding='utf-8') as sf:
                    placeholder_present = 'ultrasecretkey' in sf.read()
            except Exception:
                placeholder_present = False

        if placeholder_present and "cap_drop: - ALL" in content:
            print("First run detected for SearXNG. Temporarily removing 'cap_drop: - ALL' directive...")
            modified_content = content.replace("cap_drop: - ALL", "# cap_drop: - ALL  # Temporarily commented out for first run")
            with open(docker_compose_path, 'w', encoding='utf-8') as file:
                file.write(modified_content)
            print("Note: After the first run completes, re-add 'cap_drop: - ALL' for security.")

        elif not placeholder_present and "# cap_drop: - ALL  # Temporarily commented out for first run" in content:
            print("SearXNG appears initialized. Re-enabling 'cap_drop: - ALL' directive for security...")
            modified_content = content.replace("# cap_drop: - ALL  # Temporarily commented out for first run", "cap_drop: - ALL")
            with open(docker_compose_path, 'w', encoding='utf-8') as file:
                file.write(modified_content)

    except Exception as e:
        print(f"Error checking/modifying docker-compose.yml for SearXNG: {e}")


def parse_args():
    parser = argparse.ArgumentParser(
        description='Start the InsightsLM, Local AI and Supabase services.'
    )

    parser.add_argument(
        '-n', '--name',
        default='insights-lm',
        help='Project name for Docker Compose (default: insights-lm)'
    )

    parser.add_argument(
        '-p','--profile',
        choices=['cpu', 'gpu-nvidia', 'gpu-amd', 'none'],
        default='cpu',
        help='Profile to use for Docker Compose (default: cpu)'
    )
    
    parser.add_argument(
        '-e','--environment',
        choices=['private', 'public'],
        default='private',
        help='Environment to use for Docker Compose (default: private)'
    )

    parser.add_argument(
        '-f','--compose-files',
        nargs='*',
        default=[],
        help='Additional Docker Compose files to include when starting Supabase'
    )
    
    parser.add_argument(
        '-c','--config',
        action='store_true',
        help='Generate and print the combined docker-compose.yml content without starting services'
    )
    
    parser.add_argument(
        '-u','--update',
        action='store_true',
        help='Update Docker images and restart services'
    )

    return parser.parse_args()


def main():
    args = parse_args()

    if args.config:
        yml_content = generate_yml(args.name, args.profile, args.environment, args.compose_files)
        print(yml_content)
        return

    # Prepare environment files
    prepare_env()

    # Generate SearXNG secret key and check docker-compose.yml
    generate_searxng_secret_key()
    check_and_fix_docker_compose_for_searxng()

    stop_existing_containers(args.profile)

    # First pull all necessary images
    pull_docker_images([
        "docker-compose.yml",
        "local-ai-packaged/docker-compose.yml",
        "supabase-insights-lm/docker-compose.yml"
        ] + args.compose_files, update=args.update)

    compose_files = args.compose_files.copy()

    start_insights_lm(
        project=args.name,
        profile=args.profile,
        environment=args.environment,
        compose_files=compose_files
        )


if __name__ == "__main__":
    main()
