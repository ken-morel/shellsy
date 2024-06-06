package cmd

import (
  "fmt"

  "github.com/spf13/cobra"
)

func init() {
  rootCmd.AddCommand(dloadCmd)
}

var dloadCmd = &cobra.Command{
  Use:   "dload",
  Short: "Download from a web url",
  Long:  `The version of Shellsy software`,
  Run: func(cmd *cobra.Command, args []string) {
    if len := len(args); len != 2 {
      fmt.Println("Wrong number of arguments")
    }
  },
}
