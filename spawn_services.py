#!/usr/bin/env python3
"""
Custom Service Spawner for Syft LLM Router
Template for implementing custom chat and search service spawning.
"""
import os
import argparse
import logging
import subprocess
import sys
import time
from datetime import datetime
import requests
from syft_core import Client
from config import RunStatus, load_config

# Configure verbose logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("spawn_services.log"),
    ],
)
logger = logging.getLogger(__name__)


class CustomServiceManager:
    """Manages service spawning, monitoring, and state tracking."""

    def __init__(self, project_name: str, config_path: str):

        client = Client.load(config_path)

        # metadata path
        metadata_path = (
            client.my_datasite / "public" / "routers" / project_name / "metadata.json"
        )

        # load config
        self.config = load_config(
            syft_config_path=client.config.path,
            metadata_path=metadata_path,
        )

        # Service configuration from .env
        self.enable_chat = self.config.enable_chat
        self.enable_search = self.config.enable_search

        self.custom_chat_api_key = os.getenv("OPENROUTER_API_KEY")

        # URLs will be discovered dynamically when services are spawned
        self.custom_chat_url = None
        self.custom_search_url = None


        # Update state
        self._initialize_state()

        logger.info(f"Service Manager initialized for {project_name}")
        logger.info(f"Chat enabled: {self.enable_chat}")
        logger.info(f"Search enabled: {self.enable_search}")

    def _initialize_state(self) -> None:
        """Update state."""

        # Initialize service states based on enabled services
        if self.enable_chat:
            self.config.state.update_service_state(
                "chat",
                status=RunStatus.STOPPED,
                url=None,
                port=None,
                pid=None,
                started_at=None,
                error=None,
            )
        if self.enable_search:
            self.config.state.update_service_state(
                "search",
                status=RunStatus.STOPPED,
                url=None,
                port=None,
                pid=None,
                started_at=None,
                error=None,
            )

    def spawn_custom_chat(self) -> bool:
        """Spawn and verify DeepSeek V3 service."""
        logger.info("🔧 Setting up DeepSeek V3 service...")

        try:
             # Import and initialize the chat service
            from chat_service import CustomChatService
            
            # Check if API key is available
            if not self.custom_chat_api_key:
                raise ValueError("OPENROUTER_API_KEY is required but not found in environment variables")
            
            # Initialize the chat service with config and API key
            self.chat_service = CustomChatService(config=self.config, api_key=self.custom_chat_api_key)
            
            # Test the chat service with a simple request
            from schema import Message, Role, GenerationOptions
            test_messages = [
                Message(role=Role.USER, content="Hello, this is a test message.")
            ]
            
            logger.info("🧪 Testing chat service with a simple request...")
            test_response = self.chat_service.generate_chat(
                model="deepseek-v3",
                messages=test_messages,
                user_email="test@example.com",
                options=GenerationOptions(max_tokens=50)
            )
            
            if test_response and test_response.message.content:
                logger.info("✅ Chat service test successful")
                self.config.state.update_service_state(
                    "chat", 
                    status=RunStatus.RUNNING,
                    url=self.custom_chat_url  # This would be set if you have a URL
                )
                return True
            else:
                raise Exception("Chat service test failed - no response received")

        except Exception as e:
            logger.error(f"❌ Custom chat service setup failed: {e}")
            self.config.state.update_service_state(
                "chat", status=RunStatus.FAILED, error=str(e)
            )
            return False

    def spawn_custom_search(self) -> bool:
        """Spawn all enabled services in dependency order."""
        logger.info("🚀 Starting service spawning process...")

        try:
            # TODO: Add your custom search service setup logic here
            # Example:
            # 1. Initialize your vector database connection
            # 2. Set up embeddings model
            # 3. Load/verify document index
            # 4. Test search functionality

            # Placeholder implementation
            logger.warning("⚠️  Custom search service spawning not implemented")
            logger.info(
                "💡 Please implement spawn_custom_search() method in spawn_services.py"
            )

            # For now, mark as failed so router doesn't start
            self.config.state.update_service_state(
                "search", status=RunStatus.FAILED, error="Not implemented"
            )
            return False

        except Exception as e:
            logger.error(f"❌ Custom search service setup failed: {e}")
            self.config.state.update_service_state(
                "search", status=RunStatus.FAILED, error=str(e)
            )
            return False

    def cleanup_services(self) -> None:
        """Cleanup services on shutdown."""
        logger.info("🧹 Cleaning up services...")

        # Update router state
        self.config.state.update_router_state(status=RunStatus.STOPPED)

        # Update service states
        for service_name in self.config.state.services.keys():
            self.config.state.update_service_state(
                service_name, status=RunStatus.STOPPED
            )

        logger.info("✅ Cleanup completed")

    def _save_service_urls(self) -> None:
        """Save discovered service URLs to state and update .env file."""
        logger.info("💾 Saving discovered service URLs...")

        # Update state with discovered URLs
        if self.ollama_base_url:
            self.config.state.update_service_state("chat", url=self.ollama_base_url)

        if self.rag_service_url:
            self.config.state.update_service_state("search", url=self.rag_service_url)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Spawn services for Syft LLM Router")
    parser.add_argument("--project-name", required=True, help="Name of the project")
    parser.add_argument("--config-path", required=True, help="Path to syftbox config")
    parser.add_argument(
        "--cleanup", action="store_true", help="Cleanup services and exit"
    )

    args = parser.parse_args()

    try:
        manager = CustomServiceManager(args.project_name, args.config_path)

        if args.cleanup:
            manager.cleanup_services()
            return 0

        # Spawn services
        if manager.spawn_custom_chat():
            logger.info("🎉 All services ready - router can start")
            return 0
        else:
            logger.error("💥 Service spawning failed - router should not start")
            return 1

    except Exception as e:
        logger.error(f"💥 Service spawning error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
