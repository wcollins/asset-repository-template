#!/usr/bin/env python3
"""
Deployment script for promoting Itential assets using asyncplatform.

This script reads asset files from the repository and imports them into
the target Itential Platform environment using the asyncplatform library.

Currently supports:
    - Studio projects
    - Operations Manager automations
     - Lifecycle Manager resources

Coming soon:
    - Configuration Manager configurations

Usage:
    python deploy.py <environment>

Required environment variables:
    HOST          - Itential Platform hostname
    CLIENT_ID     - Service account client ID
    CLIENT_SECRET - Service account client secret
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import asyncplatform
from asyncplatform.models.projects import ProjectMember

class AssetDeployer:
    """Handles deployment of Itential assets to a target environment."""

    def __init__(self, environment: str, members: list[dict[str, str]] | None = None):
        """Initialize deployer with environment configuration.

        Args:
            environment: Target environment name
            members: Optional list of project members with username, type, and role
        """
        self.environment = environment
        self.members = members or []
        self.host = os.environ.get("HOST")
        self.client_id = os.environ.get("CLIENT_ID")
        self.client_secret = os.environ.get("CLIENT_SECRET")

        if not all([self.host, self.client_id, self.client_secret]):
            raise ValueError(
                "Missing required environment variables: "
                "HOST, CLIENT_ID, CLIENT_SECRET"
            )

        print(f"🚀 Deploying to {environment} environment")

    def find_asset_files(self) -> dict[str, list[Path]]:
        """Scan repository for asset files in bundle structure.

        Returns:
            Dictionary mapping asset types to list of file paths
        """
        repo_root = Path(__file__).parent.parent.parent
        assets: dict[str, list[Path]] = {
            "projects": [],
            "automations": [],
            "lifecycle_manager_resources": []
        }

        # Scan for Studio project files by looking in studio folders
        for studio_dir in repo_root.glob("*/studio"):
            if studio_dir.is_dir():
                for project_file in studio_dir.glob("*.json"):
                    assets["projects"].append(project_file)
                    print(f"📦 Found Studio project: {project_file.name}")

        # Scan for automation files by looking in operations_manager folders
        for om_dir in repo_root.glob("*/operations_manager"):
            if om_dir.is_dir():
                for automation_file in om_dir.glob("*.json"):
                    assets["automations"].append(automation_file)
                    print(f"🤖 Found Operations Manager automation: {automation_file.name}")
        
        # Scan for lifecycle manager resource files
        for lm_dir in repo_root.glob("*/lifecycle_manager"):
            if lm_dir.is_dir():
                for resource_file in lm_dir.glob("*.json"):
                    assets["lifecycle_manager_resources"].append(resource_file)
                    print(f"🔧 Found Lifecycle Manager resource: {resource_file.name}")
        
        return assets

    async def deploy_projects(self, client: Any, project_files: list[Path]) -> None:
        """Deploy Studio projects to the platform.

        Args:
            client: Asyncplatform client instance
            project_files: List of project file paths
        """
        if not project_files:
            print("ℹ️  No Studio projects to deploy")
            return

        projects_resource = client.resource("projects")

        for project_file in project_files:
            with open(project_file, "r") as f:
                project_data = json.load(f)
            project_name = project_data.get("name", project_file.stem)

            try:
                print(f"📥 Importing project: {project_name}")

                # Convert members dict to ProjectMember objects
                # Support both schemas: account (username) and group (name)
                members = []
                for member in self.members:
                    member_data = {
                        "type": member["type"],
                        "role": member["role"]
                    }
                    # Use "username" for accounts, "name" for groups
                    if member["type"] == "account":
                        member_data["username"] = member["username"]
                    else:  # type == "group"
                        member_data["name"] = member["name"]

                    members.append(ProjectMember(**member_data))

                # Import project with members (overwrite if exists)
                result = await projects_resource.importer(
                    project_data,
                    members=members,
                    overwrite=True,
                    skip_reference_validation=True
                )
                print(f"✅ Successfully imported project: {result['name']}")
                if members:
                    for member in members:
                        member_identifier = (
                            getattr(member, 'username', None) or
                            getattr(member, 'name', 'unknown')
                        )
                        print(f"👤 Added {member.type} {member_identifier} as {member.role}")
            except Exception as e:
                print(f"❌ Failed to import project {project_name}: {e}")
                raise

    async def deploy_automations(
        self, client: Any, automation_files: list[Path]
    ) -> None:
        """Deploy Operations Manager automations to the platform.

        Args:
            client: Asyncplatform client instance
            automation_files: List of automation file paths
        """
        if not automation_files:
            print("ℹ️  No automations to deploy")
            return

        automations_resource = client.resource("automations")

        for automation_file in automation_files:
            with open(automation_file, "r") as f:
                automation_data = json.load(f)
            automation_name = automation_data.get("name", automation_file.stem)

            try:
                # Check if automation already exists
                print(f"🔍 Checking if automation exists: {automation_name}")
                existing_automation = await automations_resource.get_automation_by_name(
                    automation_name
                )

                if existing_automation:
                    # Automation exists, delete it first before importing
                    print(f"📝 Automation exists, deleting existing version: {automation_name}")
                    await automations_resource.delete(automation_name)
                    print(f"🗑️  Deleted existing automation: {automation_name}")

                print(f"📥 Importing automation: {automation_name}")
                result = await automations_resource.importer(automation_data)
                print(f"✅ Successfully imported automation: {result['name']}")
            except Exception as e:
                print(f"❌ Failed to import automation {automation_name}: {e}")
                raise
    
    async def deploy_lifecycle_manager_resources(
        self, client: Any, resource_files: list[Path]
    ) -> None:
        """Deploy Lifecycle Manager resource models to the platform.

        Args:
            client: Asyncplatform client instance
            resource_files: List of lifecycle manager resource file paths
        """
        if not resource_files:
            print("ℹ️  No Lifecycle Manager resources to deploy")
            return

        lm_resource = client.resource("lifecycle_manager")
        lifecyle_manager_resource_payload = {
            "model":{} 
            }
        for resource_file in resource_files:
            with open(resource_file, "r") as f:
                resource_data = json.load(f)
                lifecyle_manager_resource_payload["model"] = resource_data
            resource_name = resource_data.get("name", resource_file.name)
            
            try:
                # Check if resource model already exists and delete before re-importing
                print(f"🔍 Checking if resource model exists: {resource_name}")
                existing_resource = await lm_resource.get_resource_by_name(resource_name)
                if existing_resource:
                    print(f"📝 Resource model exists, deleting existing version: {resource_name}")
                    await lm_resource.delete(resource_name)
                    print(f"🗑️  Deleted existing resource model: {resource_name}")
                print(f"📥 Importing resource model: {resource_name}")
                result = await lm_resource.importer(lifecyle_manager_resource_payload)
                print(f"✅ Successfully imported resource model: {result['data']['name']}")
            except Exception as e:
                print(f"❌ Failed to import resource model {resource_name}: {e}")
                raise

    async def deploy(self) -> None:
        """Execute the deployment process."""
        print(f"\n{'='*60}")
        print(f"Starting deployment to {self.environment}")
        print(f"{'='*60}\n")

        # Find all asset files
        assets = self.find_asset_files()

        if not any(assets.values()):
            print("⚠️  No assets found to deploy")
            return

        # Initialize asyncplatform client
        async with asyncplatform.client(
            host=self.host,
            client_id=self.client_id,
            client_secret=self.client_secret,
            verify=True,
        ) as client:
            print(f"\n✅ Connected to Itential Platform: {self.host}\n")

            # Deploy projects first
            await self.deploy_projects(client, assets["projects"])
            
            # Deploy Lifecycle Manager resources
            await self.deploy_lifecycle_manager_resources(
                client, assets["lifecycle_manager_resources"]
            )

            # Deploy automations
            await self.deploy_automations(client, assets["automations"])

        print(f"\n{'='*60}")
        print(f"✅ Deployment to {self.environment} completed successfully!")
        print(f"{'='*60}\n")


def main():
    """Main entry point for the deployment script."""
    if len(sys.argv) != 2:
        print("Usage: python deploy.py <environment>")
        sys.exit(1)

    environment = sys.argv[1]

    # Read members from environment variable (JSON array)
    members = []
    members_json = os.getenv("PROJECT_MEMBERS")
    if members_json:
        try:
            members = json.loads(members_json)
        except json.JSONDecodeError as e:
            print(f"⚠️  Invalid PROJECT_MEMBERS JSON: {e}")
            print("Continuing without project members")

    try:
        deployer = AssetDeployer(environment, members=members)
        asyncio.run(deployer.deploy())
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
