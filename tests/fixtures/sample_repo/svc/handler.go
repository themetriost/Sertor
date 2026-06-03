// File di esempio per i test di chunking sintattico (Go).
package svc

import "fmt"

func Greet(name string) string {
	return fmt.Sprintf("ciao %s", name)
}

func Add(a int, b int) int {
	return a + b
}
