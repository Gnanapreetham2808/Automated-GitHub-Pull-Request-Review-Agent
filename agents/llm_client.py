"""
LLM Client Wrapper for OpenAI API
Provides async interface for making LLM calls with retry logic and error handling.
"""

import asyncio
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Custom exception for LLM-related errors."""
    pass


async def llm_call(
    system_prompt: str,
    user_prompt: str,
    model: str = "gpt-4o-mini",
    max_retries: int = 3,
    timeout: float = 30.0,
    temperature: float = 0.3
) -> str:
    """
    Make an async call to OpenAI API with retry logic.
    
    Args:
        system_prompt: System message defining agent behavior
        user_prompt: User message with the content to analyze
        model: OpenAI model to use (default: gpt-4o-mini)
        max_retries: Maximum number of retry attempts
        timeout: Timeout in seconds for the request
        temperature: Temperature for response generation (0.0-2.0)
        
    Returns:
        LLM response as string
        
    Raises:
        LLMError: If API call fails after retries or configuration is invalid
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise LLMError("OPENAI_API_KEY environment variable not set")
    
    api_url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": temperature,
        "max_tokens": 2000
    }
    
    last_exception: Optional[Exception] = None
    
    for attempt in range(1, max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.debug(f"LLM call attempt {attempt}/{max_retries} to {model}")
                
                response = await client.post(api_url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    if not content:
                        raise LLMError("Empty response from LLM")
                    
                    logger.debug(f"LLM call successful (attempt {attempt})")
                    return content.strip()
                
                elif response.status_code == 401:
                    raise LLMError("Invalid OpenAI API key")
                
                elif response.status_code == 429:
                    logger.warning(f"Rate limit hit, attempt {attempt}/{max_retries}")
                    if attempt < max_retries:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    raise LLMError("OpenAI API rate limit exceeded")
                
                elif response.status_code >= 500:
                    logger.warning(f"OpenAI server error: {response.status_code}, attempt {attempt}/{max_retries}")
                    if attempt < max_retries:
                        await asyncio.sleep(1 * attempt)
                        continue
                    raise LLMError(f"OpenAI server error: {response.status_code}")
                
                else:
                    error_msg = response.text
                    raise LLMError(f"OpenAI API error {response.status_code}: {error_msg}")
        
        except httpx.TimeoutException as e:
            last_exception = e
            logger.warning(f"Request timeout on attempt {attempt}/{max_retries}")
            if attempt < max_retries:
                await asyncio.sleep(1)
                continue
            raise LLMError(f"Request timed out after {max_retries} attempts")
        
        except httpx.RequestError as e:
            last_exception = e
            logger.warning(f"Request error on attempt {attempt}/{max_retries}: {str(e)}")
            if attempt < max_retries:
                await asyncio.sleep(1)
                continue
            raise LLMError(f"Network error: {str(e)}")
        
        except LLMError:
            raise
        
        except Exception as e:
            last_exception = e
            logger.error(f"Unexpected error on attempt {attempt}/{max_retries}: {str(e)}")
            if attempt < max_retries:
                await asyncio.sleep(1)
                continue
            raise LLMError(f"Unexpected error: {str(e)}")
    
    # Should not reach here, but just in case
    if last_exception:
        raise LLMError(f"Failed after {max_retries} attempts: {str(last_exception)}")
    raise LLMError(f"Failed after {max_retries} attempts")
