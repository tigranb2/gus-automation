if [ "$1" = "open-loop-client" ]; then
  cd ../pineapple
  git stash
  git checkout open-loop-client
  git pull
  . compile.sh

  cd ../gus-epaxos
  git stash
  git checkout open-loop-epaxos
  git pull
  . compile.sh

  cd ../gryff-testing
  git stash
  git checkout open-loop-client
  git pull
  . compile.sh
else
  cd ../pineapple
  git stash
  git checkout main
  git pull
  . compile.sh

  cd ../gus-epaxos
  git stash
  git checkout main
  git pull
  . compile.sh

  cd ../gryff-testing
  git stash
  git checkout main
  git pull
  . compile.sh
fi