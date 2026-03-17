"""
Chat service — handles AI chat interactions with the chatbot service.
"""
import httpx
from sqlalchemy.orm import Session

from ..config import config
from ..models.chat import ChatRequest, ChatResponse, ChatSearchFilters, AggregationResult
from ..services.candidate_service import list_candidates


async def handle_chat_message(
    message: str,
    db: Session,
) -> ChatResponse:
    """
    Handle a chat message by communicating with the chatbot service.
    
    Args:
        message: User's chat message
        db: Database session for querying candidates
        
    Returns:
        ChatResponse with AI reply and candidate data
    """
    chatbot_url = config.chatbot_service_url
    
    try:
        # Call chatbot service for classification and filter extraction
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Classify the question
            classify_response = await client.post(
                f"{chatbot_url}/api/classify",
                json={"message": message}
            )
            classify_data = classify_response.json()
            
            # Extract filters if candidate-related
            filters = ChatSearchFilters()
            if classify_data.get("is_candidate_related", False):
                extract_response = await client.post(
                    f"{chatbot_url}/api/extract-filters",
                    json={"message": message}
                )
                extract_data = extract_response.json()
                
                filters = ChatSearchFilters(
                    position=extract_data.get("position"),
                    min_years_experience=extract_data.get("min_years_experience"),
                    max_years_experience=extract_data.get("max_years_experience"),
                    nationality=extract_data.get("nationality"),
                    current_address=extract_data.get("current_address"),
                )
            
            # Check for aggregation requests
            aggregation = None
            if classify_data.get("requires_data", False):
                agg_response = await client.post(
                    f"{chatbot_url}/api/detect-aggregation",
                    json={"message": message}
                )
                agg_data = agg_response.json()
                
                if agg_data.get("is_aggregation", False):
                    # Get candidate list for aggregation
                    candidate_list = list_candidates(
                        db=db,
                        page=1,
                        page_size=1000,  # Get all for aggregation
                        nationality=filters.nationality,
                        position=filters.position,
                        min_years_experience=filters.min_years_experience,
                        max_years_experience=filters.max_years_experience,
                        current_address=filters.current_address,
                    )
                    
                    # Calculate aggregations (use current_salary for salary stats)
                    candidates = candidate_list.items
                    if candidates:
                        salaries = [float(c.current_salary) for c in candidates if c.current_salary is not None]
                        experiences = [c.years_experience for c in candidates if c.years_experience]
                        
                        aggregation = AggregationResult(
                            total_count=len(candidates),
                            avg_salary=sum(salaries) / len(salaries) if salaries else None,
                            avg_experience=sum(experiences) / len(experiences) if experiences else None,
                            min_salary=min(salaries) if salaries else None,
                            max_salary=max(salaries) if salaries else None,
                            min_experience=min(experiences) if experiences else None,
                            max_experience=max(experiences) if experiences else None,
                        )
            
            # Get matching candidates
            candidate_list = list_candidates(
                db=db,
                page=1,
                page_size=10,  # Top 10 candidates
                nationality=filters.nationality,
                position=filters.position,
                min_years_experience=filters.min_years_experience,
                max_years_experience=filters.max_years_experience,
                current_address=filters.current_address,
            )
            
            # Generate a simple reply (in production, this would call an LLM)
            reply = _generate_reply(message, classify_data, candidate_list.total, aggregation)
            
            return ChatResponse(
                reply=reply,
                filters=filters,
                total_matches=candidate_list.total,
                top_candidates=candidate_list.items[:10],
                aggregations=aggregation,
            )
            
    except httpx.RequestError as e:
        # Fallback if chatbot service is unavailable
        return ChatResponse(
            reply="Sorry, I encountered an error connecting to the AI service. Please try again.",
            filters=ChatSearchFilters(),
            total_matches=0,
            top_candidates=[],
            aggregations=None,
        )
    except Exception as e:
        return ChatResponse(
            reply=f"Sorry, I encountered an error. Please try again. Error: {str(e)}",
            filters=ChatSearchFilters(),
            total_matches=0,
            top_candidates=[],
            aggregations=None,
        )


def _generate_reply(
    message: str,
    classify_data: dict,
    total_matches: int,
    aggregation: AggregationResult = None,
) -> str:
    """
    Generate a reply message based on classification and results.
    
    Args:
        message: Original user message
        classify_data: Classification results from chatbot service
        total_matches: Number of matching candidates
        aggregation: Optional aggregation results
        
    Returns:
        Reply message string
    """
    question_type = classify_data.get("question_type", "conversational")
    
    if question_type == "greeting":
        return "Hello! I can help you search for candidates. Try asking me something like 'Show me backend engineers' or 'What's the average salary?'"
    
    elif question_type == "aggregation":
        if aggregation:
            parts = []
            if aggregation.total_count:
                parts.append(f"Found {aggregation.total_count} candidates")
            if aggregation.avg_salary:
                parts.append(f"Average salary: ${aggregation.avg_salary:,.0f}")
            if aggregation.avg_experience:
                parts.append(f"Average experience: {aggregation.avg_experience:.1f} years")
            return ". ".join(parts) + "."
        else:
            return f"I found {total_matches} candidates matching your query."
    
    elif question_type == "candidate_search":
        if total_matches > 0:
            return f"I found {total_matches} candidate(s) matching your search. Here are the top results."
        else:
            return "I couldn't find any candidates matching your search. Try adjusting your filters."
    
    else:
        return f"I found {total_matches} candidate(s). How can I help you further?"
