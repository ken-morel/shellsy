package cmd

import (
  "fmt"
  "io/ioutil"
  "net/http"
  "os"

  "github.com/spf13/cobra"
)

func init() {
  rootCmd.AddCommand(dloadCmd)
}

func check(e error) {
  if e != nil {
    panic(e)
  }
}

var dloadCmd = &cobra.Command{
  Use:   "dload",
  Short: "Download from a web url",
  Long:  `The version of Shellsy software`,
  Run: func(cmd *cobra.Command, args []string) {
    if len := len(args); len != 2 {
      fmt.Println("Wrong number of arguments")
    }
    res, err := http.Get(args[0])
    if err != nil {
      fmt.Printf("error making http request: %s\n", err)
      return
    }
    fmt.Printf("client: got response!\n")
    fmt.Printf("client: status code: %d\n", res.StatusCode)
    f, err := os.Create(args[1])
    defer f.Close()
    check(err)
    body, err := ioutil.ReadAll(res.Body)
    check(err)
    f.Write(body)
  },
}
