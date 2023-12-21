if [ "$1" = "open-loop-client" ]; then
  cd ../pineapple
  git stash
  git checkout open-loop-client
  . compile.sh

  cd ../gus-epaxos
  git stash
  git checkout open-loop-epaxos
  . compile.sh

  cd ../gryff-testing
  git stash
  git checkout open-loop-client
  . compile.sh
else
  cd ../pineapple
  git stash
  git checkout main
  . compile.sh

  cd ../gus-epaxos
  git stash
  git checkout main
  . compile.sh

  cd ../gryff-testing
  git stash
  git checkout main
  . compile.sh
fi