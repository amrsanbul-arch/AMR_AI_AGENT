from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field, model_validator

router = APIRouter(prefix="/api/content/reel-assembly", tags=["content"])

ImageExtension = Literal["jpg", "jpeg", "png", "webp"]
AudioExtension = Literal["mp3", "m4a", "wav", "aac"]


class AssemblyScene(BaseModel):
    image_extension: ImageExtension
    duration_seconds: int = Field(ge=1, le=60)


class AssemblyPlanRequest(BaseModel):
    scenes: list[AssemblyScene] = Field(min_length=1, max_length=12)
    audio_extension: AudioExtension | None = None

    @model_validator(mode="after")
    def limit_total_duration(self) -> "AssemblyPlanRequest":
        if sum(scene.duration_seconds for scene in self.scenes) > 180:
            raise ValueError("total video duration must not exceed 180 seconds")
        return self


class AssemblyPlanResponse(BaseModel):
    output_filename: str
    width: int
    height: int
    fps: int
    duration_seconds: int
    script: str
    note_en: str
    note_ar: str


def build_render_script(request: AssemblyPlanRequest) -> AssemblyPlanResponse:
    """Generate a local FFmpeg script from allow-listed extensions and numeric durations."""
    total = sum(scene.duration_seconds for scene in request.scenes)
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        'cd -- "$(dirname -- "$0")"',
        "if ! command -v ffmpeg >/dev/null 2>&1; then",
        '  echo "FFmpeg is required. Install it locally, then run this script again." >&2',
        "  exit 127",
        "fi",
        "ffmpeg -hide_banner -y \\",
    ]
    for index, scene in enumerate(request.scenes, start=1):
        filename = f"assets/scene_{index:02d}.{scene.image_extension}"
        lines.append(f"  -loop 1 -framerate 30 -t {scene.duration_seconds} -i '{filename}' \\")

    audio_index = len(request.scenes)
    if request.audio_extension:
        lines.append(f"  -stream_loop -1 -i 'assets/soundtrack.{request.audio_extension}' \\")

    filters: list[str] = []
    for index in range(len(request.scenes)):
        filters.append(
            f"[{index}:v]scale=720:1280:force_original_aspect_ratio=increase,"
            f"crop=720:1280,setsar=1,fps=30,format=yuv420p[v{index}]"
        )
    labels = "".join(f"[v{i}]" for i in range(len(request.scenes)))
    filters.append(f"{labels}concat=n={len(request.scenes)}:v=1:a=0[outv]")
    lines.append("  -filter_complex '" + ";".join(filters) + "' \\")
    lines.extend([
        "  -map '[outv]' -c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p \\",
    ])
    if request.audio_extension:
        lines.append(f"  -map {audio_index}:a:0 -c:a aac -b:a 128k -t {total} \\")
    else:
        lines.append(f"  -an -t {total} \\")
    lines.extend(["  -movflags +faststart \\", "  'draft.mp4'"])
    return AssemblyPlanResponse(
        output_filename="draft.mp4",
        width=720,
        height=1280,
        fps=30,
        duration_seconds=total,
        script="\n".join(lines) + "\n",
        note_en=(
            "This is an export bundle, not a rendered video. It contains your selected still images "
            "and a local FFmpeg script; run it yourself on a computer or Android Termux with FFmpeg. "
            "Nothing is uploaded or published. Review the output and add any text yourself."
        ),
        note_ar=(
            "هذه حزمة تجهيز وليست فيديو مرندرًا. تضم الصور المختارة وسكربت FFmpeg محليًا؛ شغّله "
            "بنفسك على كمبيوتر أو Termux في Android بعد تثبيت FFmpeg. لن تُرفع الملفات أو تُنشر. "
            "راجع الناتج وأضف النصوص بنفسك."
        ),
    )


@router.post("/plan", response_model=AssemblyPlanResponse)
def create_assembly_plan(request: AssemblyPlanRequest) -> AssemblyPlanResponse:
    """Return a local render recipe; media files are never sent to this API."""
    return build_render_script(request)
