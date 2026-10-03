#!/bin/sh
# usage: dbdump.sh <datadir> <outdir>
D="$1"; O="$2"; mkdir -p "$O"
: > "$O/rowcounts.txt"
for db in $(find "$D" -maxdepth 1 -name '*.db' | sort); do
  n=$(basename "$db")
  sqlite3 -readonly "$db" .schema > "$O/schema_$n.sql"
  echo "== $n user_version=$(sqlite3 -readonly "$db" 'PRAGMA user_version;')" >> "$O/rowcounts.txt"
  for t in $(sqlite3 -readonly "$db" "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"); do
    echo "$t $(sqlite3 -readonly "$db" "SELECT count(*) FROM \"$t\"")" >> "$O/rowcounts.txt"
  done
done
(cd "$D" && find . -type f -print0 | sort -z | xargs -0 shasum -a 256) > "$O/files.sha256"
