#!/usr/bin/env bash
set -o nounset -o errexit

ZIPAPP_NAME="${1:-yt-feed-dl}"

__script_dir="$(dirname "$(realpath "${BASH_SOURCE[0]}")")"
__git_root="$(cd "$__script_dir" ; git rev-parse --show-toplevel)"
__output_dir="$__git_root/build/bin"
trap "rm -rf ${tmpdir:="$(mktemp -d "${XDG_CACHE_DIR:-$HOME/.cache}/zipapp.XXXXXXXX")"}" EXIT;
python -m venv "$tmpdir/venv"
source "$tmpdir/venv/bin/activate"
mkdir "${build_dir:="$tmpdir/zipapp"}"
pip install --cache-dir "$tmpdir/pip" --target "$build_dir" -- "$__git_root/"

cat <<EOF > "$build_dir/__main__.py"
from youtube_feed_download.__main__ import main
exit(main())
EOF

python -m zipapp \
    --output "$tmpdir/$ZIPAPP_NAME" \
    --python '/usr/bin/env python' \
    -- "$build_dir"

# --main youtube_feed_download.__main__:main \

mkdir -p "$__output_dir"
mv -v "$tmpdir/$ZIPAPP_NAME" "$__output_dir/"
read -p 'Press enter to clear'