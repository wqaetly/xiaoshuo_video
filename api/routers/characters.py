"""
角色管理 API 路由
"""
import base64
from typing import List, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks

from ..models.character import (
    Character,
    CharacterCreate,
    CharacterUpdate,
    CharacterListResponse,
    VoicePreviewRequest,
    VoicePreviewResponse,
    VoiceListResponse,
    VoiceOption,
    NarratorConfig,
)
from ..services.character_service import get_character_service

router = APIRouter()


@router.get("/voices", response_model=VoiceListResponse)
async def list_voices():
    """获取可用语音列表"""
    service = get_character_service()
    voices = service.get_voice_list()
    return VoiceListResponse(voices=[VoiceOption(**v) for v in voices])


@router.get("/{project_name}", response_model=CharacterListResponse)
async def list_characters(project_name: str):
    """获取角色列表"""
    service = get_character_service()
    result = service.list_characters(project_name)
    return CharacterListResponse(
        characters=[Character(**c) for c in result["characters"]],
        total=result["total"],
        narrator=NarratorConfig(**result["narrator"]) if result.get("narrator") else None,
    )


@router.get("/{project_name}/{character_id}", response_model=Character)
async def get_character(project_name: str, character_id: str):
    """获取角色详情"""
    service = get_character_service()
    char = service.get_character(project_name, character_id)
    if char is None:
        raise HTTPException(status_code=404, detail=f"角色不存在: {character_id}")
    return Character(**char)


@router.post("/{project_name}", response_model=Character)
async def create_character(project_name: str, character: CharacterCreate):
    """创建角色"""
    service = get_character_service()
    try:
        result = service.create_character(project_name, character.model_dump())
        return Character(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建角色失败: {e}")


@router.put("/{project_name}/{character_id}", response_model=Character)
async def update_character(
    project_name: str, character_id: str, character: CharacterUpdate
):
    """更新角色"""
    service = get_character_service()
    result = service.update_character(
        project_name, character_id, character.model_dump(exclude_unset=True)
    )
    if result is None:
        raise HTTPException(status_code=404, detail=f"角色不存在: {character_id}")
    return Character(**result)


@router.delete("/{project_name}/{character_id}")
async def delete_character(project_name: str, character_id: str):
    """删除角色"""
    service = get_character_service()
    if not service.delete_character(project_name, character_id):
        raise HTTPException(status_code=404, detail=f"角色不存在: {character_id}")
    return {"message": f"角色 {character_id} 已删除"}


@router.post("/{project_name}/{character_id}/regenerate")
async def regenerate_character_image(
    project_name: str, character_id: str, background_tasks: BackgroundTasks
):
    """重新生成角色立绘"""
    service = get_character_service()
    try:
        result = service.regenerate_character_image(project_name, character_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"角色不存在: {character_id}")
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_name}/voice/preview", response_model=VoicePreviewResponse)
async def preview_voice(project_name: str, request: VoicePreviewRequest):
    """预览语音"""
    service = get_character_service()
    audio_data = service.preview_voice(request.text, request.voice_id)
    if audio_data is None:
        return VoicePreviewResponse(audio_data=None, message="语音合成失败")

    # 转换为 Base64
    audio_base64 = base64.b64encode(audio_data).decode("utf-8")
    return VoicePreviewResponse(audio_data=audio_base64, message="成功")

