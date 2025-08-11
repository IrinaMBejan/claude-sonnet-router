"""Chat service implementation using DeepSeek V3."""

import os
from typing import List, Optional
from uuid import uuid4

import requests
from loguru import logger

from base_services import ChatService
from schema import (
    ChatResponse,
    GenerationOptions,
    Message,
    ChatUsage,
    PublishedMetadata,
    RouterServiceType,
    FinishReason, Role
)
from config import RouterConfig
from pydantic import EmailStr
from syft_accounting_sdk import UserClient


class CustomChatService(ChatService):
    """DeepSeek service implementation using OpenRouter."""


    def __init__(self, config: RouterConfig, api_key: Optional[str] = None):
        """Initialize DeepSeek chat service via OpenRouter."""

        super().__init__(config)
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        
        if not self.api_key:
            raise ValueError("OpenRouter API key is required. Set OPENROUTER_API_KEY environment variable or pass api_key parameter.")
            
        self.base_url = "https://openrouter.ai/api/v1"
        self.allowed_models = [
            "deepseek-chat",
        ]
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "X-Title": "Router"
        }

        self.accounting_client: UserClient = self.config.accounting_client()
        logger.info(f"Initialized accounting client: {self.accounting_client}")

        self.app_name = self.config.project.name


    def _validate_model(self, model: str) -> str:
        """Validate that the model is allowed and return the full model name.

        Args:
            model: The model identifier.

        Returns:
            The full model name for OpenRouter.

        Raises:
            ValueError: If the model is not allowed.
        """
        # if model not in self.allowed_models:
        #     allowed_models_str = ", ".join(self.allowed_models)
        #     raise ValueError(
        #         f"Model '{model}' is not allowed. Allowed models: {allowed_models_str}"
        #     )
        # Default to deepseek-chat
        if model not in self.allowed_models:
            logger.warning(f"Model '{model}' is not allowed, defaulting to 'deepseek-chat'.")
            model = "deepseek-chat"

        # Map short names to full OpenRouter model names
        model_mapping = {
            "deepseek-chat": "deepseek/deepseek-chat",
            "deepseek-coder": "deepseek/deepseek-coder",
            "deepseek-v3": "deepseek/deepseek-v3"
        }

        return model_mapping.get(model, model)

    def _map_finish_reason(self, finish_reason: str) -> FinishReason:
        """Map OpenRouter finish reason to our FinishReason enum.

        Args:
            finish_reason: The finish reason from OpenRouter.

        Returns:
            The corresponding FinishReason enum value.
        """
        mapping = {
            "stop": FinishReason.STOP,
            "length": FinishReason.LENGTH,
            "content_filter": FinishReason.CONTENT_FILTER,
        }
        return mapping.get(finish_reason, None)

    def __make_chat_request(self, payload: dict) -> str:
        """Make a chat request to OpenRouter."""
        url = f"{self.base_url}/chat/completions"
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    def generate_chat(
        self,
        model: str,
        messages: List[Message],
        user_email: EmailStr,
        transaction_token: Optional[str] = None,
        options: Optional[GenerationOptions] = None,
    ) -> ChatResponse:
        """Generate a chat response using DeepSeek via OpenRouter."""
        try:
            full_model_name = self._validate_model(model)

            # Convert our Message objects to OpenRouter format
            openrouter_messages = []
            for message in messages:
                openrouter_message = {
                    "role": message.role.value.lower(),
                    "content": message.content,
                }
                openrouter_messages.append(openrouter_message)

            # Prepare the request payload
            payload = {
                "model": full_model_name,
                "messages": openrouter_messages,
                "max_tokens": 1000,  # Default max tokens
            }
        
            # Add options if provided
            if options:
                if options.max_tokens is not None:
                    payload["max_tokens"] = options.max_tokens
                if options.temperature is not None:
                    payload["temperature"] = options.temperature
                if options.top_p is not None:
                    payload["top_p"] = options.top_p
                if options.stop_sequences is not None:
                    payload["stop"] = options.stop_sequences

            # Initialize query cost to 0.0
            query_cost = 0.0

            # Add generation options if provided
            if options:
                if options.temperature is not None:
                    payload["temperature"] = options.temperature
                if options.top_p is not None:
                    payload["top_p"] = options.top_p
                if options.max_tokens is not None:
                    payload["num_predict"] = options.max_tokens
                if options.stop_sequences:
                    payload["stop"] = options.stop_sequences

            if self.pricing > 0 and transaction_token:
                # If pricing is not zero, then we need to create a transaction
                with self.accounting_client.delegated_transfer(
                    user_email,
                    amount=self.pricing,
                    token=transaction_token,
                    app_name=self.app_name,
                    app_ep_path="/chat",
                ) as payment_txn:
                    # Make request to DeepSeek via OpenRouter
                    content = self.__make_chat_request(payload)

                    # If the response is not empty, confirm the transaction
                    if content:
                        payment_txn.confirm()
                        query_cost = self.pricing

            elif self.pricing > 0 and not transaction_token:
                # If pricing is not zero, but transaction token is not provided, then we raise an error
                raise ValueError(
                    "Transaction token is required for paid services. Please provide a transaction token."
                )

            else:
                # If pricing is zero, then we make a request to DeepSeek without creating a transaction
                # We don't need to create a transaction because the service is free
                # Make request to DeepSeek via OpenRouter
                content = self.__make_chat_request(payload)

            
            # Parse the response
            response_data = content
                
            # Extract usage information
            usage_data = response_data.get("usage", {})
            usage = ChatUsage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )

            # Extract the generated message and other information
            choices = response_data.get("choices", [{}])
            choice = choices[0] if choices else {}
            message_data = choice.get("message", {})
            
            # Create the Message object
            generated_message = Message(
                role=Role.ASSISTANT,
                content=message_data.get("content", ""),
            )


            # Get finish reason
            finish_reason_str = choice.get("finish_reason")
            finish_reason = (
                self._map_finish_reason(finish_reason_str) if finish_reason_str else None
            )

            return ChatResponse(
                id=uuid4(),
                model=model,
                message=generated_message,
                finish_reason=finish_reason,                usage=usage,
                provider_info={"provider": "deepseek", "model": model},
                cost=query_cost,
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"DeepSeek API request failed: {e}")
            raise e
        except Exception as e:
            logger.error(f"Unexpected error in chat generation: {e}")
            raise e

    @property
    def pricing(self) -> float:
        """Get the pricing for the chat service."""
        if not self.config.metadata_path.exists():
            return 0.0
        metadata = PublishedMetadata.from_path(self.config.metadata_path)
        for service in metadata.services:
            if service.type == RouterServiceType.CHAT:
                return service.pricing


ChatServiceImpl = CustomChatService
