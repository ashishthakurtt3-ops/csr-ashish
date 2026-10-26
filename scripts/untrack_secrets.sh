#!/usr/bin/env bash
# Stop tracking secrets / databases that were committed by mistake. Run once from the repo root.
set -e
git rm --cached -r --ignore-unmatch .env db.sqlite3 'db.sqlite3.*' '*.sqlite3' '*.sqlite3.*' runserver.log runserver_err.log
git commit -m "Stop tracking .env, SQLite databases and logs"
echo "Now rotate every credential that was in .env (MySQL password, SECRET_KEY, e-mail password)."
echo "To purge them from history use: git filter-repo --path .env --path-glob '*.sqlite3*' --invert-paths"
