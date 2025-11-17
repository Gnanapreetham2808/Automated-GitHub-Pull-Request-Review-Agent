"""
LLM Client Wrapper for Google Gemini API
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
    model: str = "gemini-1.5-flash",
    max_retries: int = 3,
    timeout: float = 30.0,
    temperature: float = 0.3
) -> str:
    """
    Make an async call to Google Gemini API with retry logic.
    
    Args:
        system_prompt: System message defining agent behavior
        user_prompt: User message with the content to analyze
        model: Gemini model to use (default: gemini-1.5-flash)
        max_retries: Maximum number of retry attempts
        timeout: Timeout in seconds for the request
        temperature: Temperature for response generation (0.0-2.0)
        
    Returns:
        LLM response as string
        
    Raises:
        LLMError: If API call fails after retries or configuration is invalid
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise LLMError("GEMINI_API_KEY environment variable not set")
    
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {
        "Content-Type": "application/json"
    }
    
    # Combine system and user prompts for Gemini
    combined_prompt = f"{system_prompt}\n\n{user_prompt}"
    
    payload = {
        "contents": [{
            "parts": [{
                "text": combined_prompt
            }]
        }],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": 2000,
        }
    }
    
    last_exception: Optional[Exception] = None
    
    for attempt in range(1, max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.debug(f"Gemini API call attempt {attempt}/{max_retries} using {model}")
                
                response = await client.post(api_url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    # Extract content from Gemini response format
                    candidates = data.get("candidates", [])
                    if not candidates:
                        raise LLMError("Empty response from LLM")
                    
                    content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    
                    if not content:
                        raise LLMError("Empty response from LLM")
                    
                    logger.debug(f"LLM call successful (attempt {attempt})")
                    return content.strip()
                
                elif response.status_code == 400:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Invalid request")
                    raise LLMError(f"Invalid Gemini API request: {error_msg}")
                
                elif response.status_code == 403:
                    raise LLMError("Invalid Gemini API key or permission denied")
                
                elif response.status_code == 429:
                    logger.warning(f"Rate limit hit, attempt {attempt}/{max_retries}")
                    if attempt < max_retries:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    raise LLMError("Gemini API rate limit exceeded")
                
                elif response.status_code >= 500:
                    logger.warning(f"Gemini server error: {response.status_code}, attempt {attempt}/{max_retries}")
                    if attempt < max_retries:
                        await asyncio.sleep(1 * attempt)
                        continue
                    raise LLMError(f"Gemini server error: {response.status_code}")
                
                else:
                    error_msg = response.text
                    raise LLMError(f"Gemini API error {response.status_code}: {error_msg}")
        
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
