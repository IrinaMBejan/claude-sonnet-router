"""Router implementation for deepseek-v3"""

from typing import List, Optional
from uuid import UUID

from schema import (
    ChatResponse,
    GenerationOptions,
    Message,
    SearchOptions,
    SearchResponse,
)

from base_services import ChatService, SearchService
from config import RouterConfig
from pydantic import EmailStr


class RouterFactory:
    """Factory for creating service instances based on configuration."""
    
    @staticmethod
    def create_chat_service(config: RouterConfig) -> ChatService:
        """Create chat service instance."""
        try:
            from chat_service import ChatServiceImpl
            return ChatServiceImpl(config)
        except ImportError:
            raise ImportError("Chat service implementation not found")
    
    @staticmethod
    def create_search_service(config: RouterConfig) -> SearchService:
        """Create search service instance."""
        try:
            from search_service import SearchServiceImpl
            return SearchServiceImpl(config)
        except ImportError:
            raise ImportError("Search service implementation not found")


class SyftLLMRouter:
    """Syft LLM Router that orchestrates chat and search services."""

    def __init__(self, config: RouterConfig):
        """Initialize the router with configured services."""
        self.config = config
        
        # Initialize services using factory pattern
        self.chat_service = None
        self.search_service = None
        
        if self.config.enable_chat:
            self.chat_service = RouterFactory.create_chat_service(self.config)
        
        if self.config.enable_search:
            self.search_service = RouterFactory.create_search_service(self.config)

    def generate_chat(
        self,
        model: str,
        messages: List[Message],
        user_email: EmailStr,
        transaction_token: Optional[str] = None,
        options: Optional[GenerationOptions] = None,
    ) -> ChatResponse:
        """Generate a chat response based on conversation history."""
        if not self.chat_service:
            raise NotImplementedError("Chat functionality is not enabled")
        return self.chat_service.generate_chat(
            model=model,
            messages=messages,
            user_email=user_email,
            transaction_token=transaction_token,
            options=options,
        )

    def search_documents(
        self,
        user_email: EmailStr,
        query: str,
        options: Optional[SearchOptions] = None,
        transaction_token: Optional[str] = None,
    ) -> SearchResponse:
        """Search documents from the index based on a search query."""
        if not self.search_service:
            raise NotImplementedError("Search functionality is not enabled")
        return self.search_service.search_documents(
            user_email=user_email,
            query=query,
            options=options,
            transaction_token=transaction_token,
        )
