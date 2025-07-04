# backend/routers/mcp.py

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_

from backend.database_setup import get_db, MCP as DBMCP, User as DBUser, UserStarredDiscussion
from backend.session import get_current_active_user, get_user_lollms_client, user_sessions
from backend.models import (
    MCPCreate, MCPUpdate, MCPPublic, ToolInfo, 
    DiscussionToolsUpdate, DiscussionInfo, UserAuthDetails
)
# Import the new discussion helper
from backend.discussion import get_user_discussion

mcp_router = APIRouter(prefix="/api/mcps", tags=["MCPs and Tools"])
discussion_tools_router = APIRouter(prefix="/api/discussions", tags=["MCPs and Tools"])

def _invalidate_user_mcp_cache(username: str):
    """Invalidates the lollms_client and tools cache for a given user."""
    if username in user_sessions:
        user_sessions[username]['lollms_client'] = None
        if 'tools_cache' in user_sessions[username]:
            user_sessions[username]['tools_cache'] = None
            print(f"INFO: Invalidated tools cache for user: {username}")

@mcp_router.post("/personal", response_model=MCPPublic, status_code=201)
def create_personal_mcp(
    mcp_data: MCPCreate,
    db: Session = Depends(get_db),
    current_user: UserAuthDetails = Depends(get_current_active_user),
):
    user_db = db.query(DBUser).filter(DBUser.username == current_user.username).one()
    new_mcp = DBMCP(**mcp_data.model_dump(), owner_user_id=user_db.id)
    db.add(new_mcp)
    try:
        db.commit()
        db.refresh(new_mcp)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An MCP with this name already exists for your account.")
    
    # Invalidate client and tools cache since the MCP list has changed
    _invalidate_user_mcp_cache(current_user.username)

    return MCPPublic(
        id=new_mcp.id, name=new_mcp.name, url=new_mcp.url,
        owner_username=user_db.username,
        created_at=new_mcp.created_at, updated_at=new_mcp.updated_at
    )

@mcp_router.get("", response_model=List[MCPPublic])
def list_my_mcps(
    db: Session = Depends(get_db),
    current_user: UserAuthDetails = Depends(get_current_active_user),
):
    user_db = db.query(DBUser).filter(DBUser.username == current_user.username).one()
    
    # Eagerly load the owner to avoid multiple queries in the loop
    mcps_db = db.query(DBMCP).options(joinedload(DBMCP.owner)).filter(
        or_(DBMCP.owner_user_id == user_db.id, DBMCP.owner_user_id == None)
    ).all()

    response = [
        MCPPublic(
            id=mcp.id, name=mcp.name, url=mcp.url,
            owner_username=mcp.owner.username if mcp.owner else None,
            created_at=mcp.created_at, updated_at=mcp.updated_at
        ) for mcp in mcps_db
    ]
    return response

@mcp_router.put("/{mcp_id}", response_model=MCPPublic)
def update_mcp(
    mcp_id: str,
    mcp_update: MCPUpdate,
    db: Session = Depends(get_db),
    current_user: UserAuthDetails = Depends(get_current_active_user),
):
    mcp_db = db.query(DBMCP).filter(DBMCP.id == mcp_id).first()
    if not mcp_db:
        raise HTTPException(status_code=404, detail="MCP not found.")

    user_db = db.query(DBUser).filter(DBUser.username == current_user.username).one()
    is_owner = mcp_db.owner_user_id == user_db.id

    if not is_owner:
        raise HTTPException(status_code=403, detail="You can only edit your own MCPs.")

    update_data = mcp_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(mcp_db, key, value)
    
    try:
        db.commit()
        db.refresh(mcp_db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An MCP with the new name already exists.")

    # Invalidate client and tools cache since the MCP list has changed
    _invalidate_user_mcp_cache(current_user.username)

    return MCPPublic(
        id=mcp_db.id, name=mcp_db.name, url=mcp_db.url,
        owner_username=user_db.username,
        created_at=mcp_db.created_at, updated_at=mcp_db.updated_at
    )

@mcp_router.delete("/{mcp_id}", status_code=204)
def delete_mcp(
    mcp_id: str,
    db: Session = Depends(get_db),
    current_user: UserAuthDetails = Depends(get_current_active_user),
):
    mcp_db = db.query(DBMCP).filter(DBMCP.id == mcp_id).first()
    if not mcp_db:
        raise HTTPException(status_code=404, detail="MCP not found.")

    user_db = db.query(DBUser).filter(DBUser.username == current_user.username).one()
    is_owner = mcp_db.owner_user_id == user_db.id
    
    if not is_owner:
        raise HTTPException(status_code=403, detail="You can only delete your own MCPs.")

    db.delete(mcp_db)
    db.commit()
    # Invalidate client and tools cache since the MCP list has changed
    _invalidate_user_mcp_cache(current_user.username)
    return None

@mcp_router.post("/reload", status_code=200)
def reload_user_lollms_client(current_user: UserAuthDetails = Depends(get_current_active_user)):
    """
    Forces a re-initialization of the lollms_client and its associated tools cache for the current user.
    This should be called after any MCP server configuration change.
    """
    _invalidate_user_mcp_cache(current_user.username)
    
    # The next call to get_user_lollms_client and list_all_available_tools will automatically rebuild.
    # We can proactively rebuild the client here to be ready for the next call.
    get_user_lollms_client(current_user.username)
    print(f"INFO: Triggered lollms_client reload for user: {current_user.username}")
    return {"status": "success", "message": "MCP client and tools cache re-initialized."}

@mcp_router.get("/tools", response_model=List[ToolInfo])
def list_all_available_tools(current_user: UserAuthDetails = Depends(get_current_active_user)):
    """
    Lists all available tools for the user.
    Results are cached per user session and are re-fetched only when MCP configurations change
    or a manual reload is triggered.
    """
    username = current_user.username
    if username not in user_sessions:
        user_sessions[username] = {}

    # Check for a valid cache first
    cached_tools = user_sessions[username].get('tools_cache')
    if cached_tools is not None:
        print(f"INFO: Serving cached tools for user: {username}")
        return cached_tools

    # If cache is invalid or missing, rebuild it
    print(f"INFO: Building tools cache for user: {username}")
    try:
        lc = get_user_lollms_client(username)
        if not hasattr(lc, 'mcp') or not lc.mcp:
            # Cache an empty list to avoid re-fetching if there's no MCP
            user_sessions[username]['tools_cache'] = []
            return []
        
        # force_refresh=True ensures we get the latest from the MCP server itself
        tools = lc.mcp.discover_tools(force_refresh=True)
        all_tools = [ToolInfo(name=item["name"], description=item.get('description', '')) for item in tools]
        sorted_tools = sorted(all_tools, key=lambda x: x.name)
        
        # Store the newly fetched tools in our cache
        user_sessions[username]['tools_cache'] = sorted_tools
        return sorted_tools
    except Exception as e:
        print(f"Error discovering tools for user {username}: {e}")
        # In case of an error, return an empty list but do not update the cache.
        # This allows for a retry on the next request.
        return []

@discussion_tools_router.get("/{discussion_id}/tools", response_model=List[ToolInfo])
def get_discussion_tools(
    discussion_id: str,
    current_user: UserAuthDetails = Depends(get_current_active_user),
):
    # Use the new discussion helper
    discussion_obj = get_user_discussion(current_user.username, discussion_id)
    if not discussion_obj:
        raise HTTPException(status_code=404, detail="Discussion not found.")

    # This call will now be much faster due to caching
    all_available_tools = list_all_available_tools(current_user)
    
    # Get active tools from the discussion's metadata
    metadata = discussion_obj.metadata or {}
    active_tool_names = set(metadata.get('active_tools', []))

    for tool in all_available_tools:
        if tool.name in active_tool_names:
            tool.is_active = True
            
    return all_available_tools

@discussion_tools_router.put("/{discussion_id}/tools", response_model=DiscussionInfo)
async def update_discussion_tools(
    discussion_id: str,
    update_request: DiscussionToolsUpdate,
    db: Session = Depends(get_db),
    current_user: UserAuthDetails = Depends(get_current_active_user),
):
    # Use the new discussion helper
    discussion_obj = get_user_discussion(current_user.username, discussion_id)
    if not discussion_obj:
        raise HTTPException(status_code=404, detail="Discussion not found.")

    # Store active tools in the discussion's metadata
    if discussion_obj.metadata is None:
        discussion_obj.metadata = {}
    discussion_obj.metadata['active_tools'] = update_request.tools
    discussion_obj.commit() # Save changes to the discussion's database

    user_db = db.query(DBUser).filter(DBUser.username == current_user.username).one()
    is_starred = db.query(UserStarredDiscussion).filter_by(user_id=user_db.id, discussion_id=discussion_id).first() is not None

    return DiscussionInfo(
        id=discussion_obj.id,
        title=discussion_obj.metadata.get('title', 'Untitled'),
        is_starred=is_starred,
        rag_datastore_ids=discussion_obj.metadata.get('rag_datastore_ids'),
        active_tools=update_request.tools,
        active_branch_id=discussion_obj.active_branch_id,
        created_at=discussion_obj.created_at,
        last_activity_at=discussion_obj.updated_at
    )