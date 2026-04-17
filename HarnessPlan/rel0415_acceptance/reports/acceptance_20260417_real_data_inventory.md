# 0415 Acceptance Real Data Inventory

## Date
- 2026-04-17

## Source Record
- `tests/test_cujiian/manual_case_config.json`

## Recorded Real Data Paths
- Video: `/Volumes/XIAOMA-A-1T/wei_videodb/C2384.MP4`
- Reference text: `/Volumes/XIAOMA-A-1T/wei_videodb/ref.txt`

## Verification
- `test -r /Volumes/XIAOMA-A-1T/wei_videodb/C2384.MP4`
- `test -r /Volumes/XIAOMA-A-1T/wei_videodb/ref.txt`
- `ffprobe -v error -show_entries format=duration,size -of json /Volumes/XIAOMA-A-1T/wei_videodb/C2384.MP4`
- `wc -c /Volumes/XIAOMA-A-1T/wei_videodb/ref.txt`

## Result
- Video path readable: `YES`
- Reference text path readable: `YES`
- Video size: `3,825,788,875` bytes
- Video duration: `540.0395` seconds
- Reference text size: `5161` bytes

## Acceptance Decision
- This data set is still present and can be used for the final 0415 acceptance round.
