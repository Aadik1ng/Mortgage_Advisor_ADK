"""
Deployment script for UAE Mortgage Assistant.

Supports deployment to:
- Local development
- Docker container
- Google Cloud Run
- Vertex AI Agent Engine
"""

import os
import subprocess
import argparse
from pathlib import Path


def deploy_local():
    """Run the server locally for development."""
    print("🏠 Starting UAE Mortgage Assistant locally...")
    subprocess.run([
        "uvicorn", 
        "server:app", 
        "--host", "0.0.0.0", 
        "--port", "8000",
        "--reload"
    ])


def deploy_docker():
    """Build and run Docker container."""
    print("🐳 Building Docker image...")
    
    # Build image
    subprocess.run([
        "docker", "build", 
        "-t", "uae-mortgage-assistant",
        "."
    ], check=True)
    
    print("🚀 Starting container...")
    
    # Run container
    subprocess.run([
        "docker", "run",
        "-p", "8000:8000",
        "-e", f"GOOGLE_API_KEY={os.getenv('GOOGLE_API_KEY', '')}",
        "-e", f"OPENAI_API_KEY={os.getenv('OPENAI_API_KEY', '')}",
        "uae-mortgage-assistant"
    ])


def deploy_cloud_run(project_id: str, region: str = "us-central1"):
    """Deploy to Google Cloud Run."""
    print(f"☁️ Deploying to Cloud Run in {region}...")
    
    image_name = f"gcr.io/{project_id}/uae-mortgage-assistant"
    
    # Build and push image
    subprocess.run([
        "gcloud", "builds", "submit",
        "--tag", image_name,
        "--project", project_id
    ], check=True)
    
    # Deploy to Cloud Run
    subprocess.run([
        "gcloud", "run", "deploy", "uae-mortgage-assistant",
        "--image", image_name,
        "--platform", "managed",
        "--region", region,
        "--allow-unauthenticated",
        "--set-env-vars", f"GOOGLE_API_KEY={os.getenv('GOOGLE_API_KEY', '')}",
        "--project", project_id
    ], check=True)
    
    print("✅ Deployment complete!")


def main():
    parser = argparse.ArgumentParser(description="Deploy UAE Mortgage Assistant")
    parser.add_argument(
        "target",
        choices=["local", "docker", "cloud-run"],
        help="Deployment target"
    )
    parser.add_argument(
        "--project",
        help="GCP project ID (for cloud-run)"
    )
    parser.add_argument(
        "--region",
        default="us-central1",
        help="GCP region (for cloud-run)"
    )
    
    args = parser.parse_args()
    
    if args.target == "local":
        deploy_local()
    elif args.target == "docker":
        deploy_docker()
    elif args.target == "cloud-run":
        if not args.project:
            print("❌ --project is required for cloud-run deployment")
            return
        deploy_cloud_run(args.project, args.region)


if __name__ == "__main__":
    main()
