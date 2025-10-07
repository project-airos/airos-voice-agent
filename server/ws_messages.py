"""Schemas for WebSocket messages exchanged with the client."""

from __future__ import annotations

from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field


class ClientMessageBase(BaseModel):
    """Common base for inbound WebSocket messages."""

    type: str
    session_id: Optional[str] = Field(
        default=None, description="Optional session identifier echoed by the client"
    )


class UserQuestionText(ClientMessageBase):
    """Text question from the client."""

    type: Literal["user.question.text"] = "user.question.text"
    text: str


class UserAudioChunk(ClientMessageBase):
    """PCM audio frame from the client."""

    type: Literal["user.audio.chunk"] = "user.audio.chunk"
    seq: int
    base64: str


class UserAudioEnd(ClientMessageBase):
    """Indicates the end of an audio stream."""

    type: Literal["user.audio.end"] = "user.audio.end"
    seq: int


class UserControl(ClientMessageBase):
    """Control actions for slide playback."""

    type: Literal["user.control"] = "user.control"
    action: Literal["pause", "resume", "next", "prev"]


ClientMessage = Annotated[
    Union[UserQuestionText, UserAudioChunk, UserAudioEnd, UserControl],
    Field(discriminator="type"),
]


class ServerMessageBase(BaseModel):
    """Base type for all outbound messages."""

    type: str


class AsrPartial(ServerMessageBase):
    """Partial ASR hypothesis."""

    type: Literal["asr.partial"] = "asr.partial"
    text: str


class AsrFinal(ServerMessageBase):
    """Final ASR result."""

    type: Literal["asr.final"] = "asr.final"
    text: str


class TutorAnswerText(ServerMessageBase):
    """Tutor response rendered as text."""

    type: Literal["tutor.answer.text"] = "tutor.answer.text"
    text: str


class TtsAudioChunk(ServerMessageBase):
    """Chunk of synthesized audio."""

    type: Literal["tts.audio.chunk"] = "tts.audio.chunk"
    seq: int
    base64: str


class TtsAudioEnd(ServerMessageBase):
    """End marker for a synthesized audio stream."""

    type: Literal["tts.audio.end"] = "tts.audio.end"
    seq: int


class SlideGoto(ServerMessageBase):
    """Instruction for the Reveal.js client to navigate to a section."""

    type: Literal["slide.goto"] = "slide.goto"
    section_id: str


class BranchSuggest(ServerMessageBase):
    """Recommendation to explore a lecture branch."""

    type: Literal["branch.suggest"] = "branch.suggest"
    branch_id: str
    title: str


ServerMessage = Annotated[
    Union[
        AsrPartial,
        AsrFinal,
        TutorAnswerText,
        TtsAudioChunk,
        TtsAudioEnd,
        SlideGoto,
        BranchSuggest,
    ],
    Field(discriminator="type"),
]
