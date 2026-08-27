#!/usr/bin/env bash
# 安装 comfyui-suite 的 7 个可调用 skill 入口到项目级 skills 根。
# DSH 只扫描 skills 根的一层目录，故为每个子 skill 建薄目录 + softlink 指向源文件。
set -euo pipefail

SUITE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"     # comfyui-suite 根
PROJECT="$(dirname "$SUITE")"                                # 项目根（.dsh 所在层）
DEST_ROOT="$PROJECT/.dsh/skills"                             # 项目级 skills 根

mkdir -p "$DEST_ROOT"

link_skill() {
  local entry_dir="$1"   # comfyui-suite 内相对目录，或 "." 表示总入口本体
  local name="$2"
  local mk="$DEST_ROOT/$name"
  mkdir -p "$mk"
  if [ "$entry_dir" = "." ]; then
    # 总入口：整个 skill 目录本体
    ln -sfn "$SUITE" "$mk"
  else
    # 子 skill：薄目录 + 指向源 SKILL.md 的 softlink
    ln -sfn "$SUITE/$entry_dir/SKILL.md" "$mk/SKILL.md"
  fi
  echo "  linked /$name"
}

echo "安装 skill 入口到 $DEST_ROOT"
link_skill "."                             comfyui-suite
link_skill "skills/text-to-image"          comfyui-text-to-image
link_skill "skills/image-to-image"         comfyui-image-to-image
link_skill "skills/text-to-video"          comfyui-text-to-video
link_skill "skills/image-to-video"         comfyui-image-to-video
link_skill "skills/reference-to-video"     comfyui-reference-to-video
link_skill "skills/prompt-optimizer"       comfyui-prompt-optimizer
echo "完成。重载技能目录后可用 /comfyui-suite 或 /comfyui-<type> 调用。"
