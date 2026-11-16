#!/bin/bash
# SpatialSight - run in Terminal (shows live logs; useful for debugging)
DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$DIR/SpatialSight.app/Contents/MacOS/SpatialSight"
