#!/bin/bash
# 起跑前把「环境里带着的答案」修掉:只保留当前分支(=base_commit)可达的历史,其余 refs/tags/reflog/悬空对象全删。
# 用法: sanitize_testbed.sh <repo目录>   ;断言失败 exit 9(装置自检:可达对象=HEAD祖先 且 无 unreachable)
set -u
R="$1"; cd "$R" || exit 9
cur=$(git rev-parse --abbrev-ref HEAD 2>/dev/null) || exit 9
before_all=$(git rev-list --all 2>/dev/null | wc -l); head_n=$(git rev-list HEAD | wc -l)
if [ "$cur" = "HEAD" ]; then git for-each-ref --format='%(refname)' | xargs -r -n1 git update-ref -d
else git for-each-ref --format='%(refname)' | grep -v -x "refs/heads/$cur" | xargs -r -n1 git update-ref -d; fi
git stash clear 2>/dev/null; git reflog expire --expire=now --all 2>/dev/null; git gc --prune=now -q 2>/dev/null
after_all=$(git rev-list --all | wc -l); unreach=$(git fsck --unreachable --no-reflogs 2>/dev/null | grep -c unreachable)
echo "SANITIZE repo=$R branch=$cur commits all:$before_all->$after_all head:$head_n unreachable:$unreach"
[ "$after_all" = "$head_n" ] && [ "$unreach" = "0" ] || { echo "SANITIZE-ASSERT-FAIL"; exit 9; }
