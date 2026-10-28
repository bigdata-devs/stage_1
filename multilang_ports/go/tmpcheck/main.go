package main

import (
	"fmt"
	"os"
	"search_engine_bench/utils"
)

func main() {
	data, err := os.ReadFile(os.Args[1])
	if err != nil {
		panic(err)
	}
	tokens := utils.Normalize(utils.Tokenize(string(data)))
	fmt.Fprintln(os.Stderr, "GO count:", len(tokens))
	for _, token := range tokens {
		fmt.Println(token)
	}
}
