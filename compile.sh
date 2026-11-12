echo "Compiling engine . . ."
clang -dynamiclib -o engine.dylib engine.c -arch arm64
echo "Compiling bot . . ."
clang -dynamiclib -o bot.dylib bot.c -arch arm64
echo "Done"
