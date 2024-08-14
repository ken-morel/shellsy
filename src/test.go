// go build -o test.so -buildmode=c-shared .
package main

import "C"
import "fmt"

//export Hello
func Hello(name *C.char) {
    fmt.Printf("Hello, %s!\n", C.GoString(name))
}

func main() {}
