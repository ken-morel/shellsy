package cmd

import (
  "fmt"

  "github.com/spf13/cobra"
)

func init() {
  rootCmd.AddCommand(versionCmd)
}

var versionCmd = &cobra.Command{
  Use:   "version",
  Short: "Print the version number of Shellsy",
  Long:  `The version of Shellsy software`,
  Run: func(cmd *cobra.Command, args []string) {
    fmt.Println("Shellsy v1.0.0-alpha")
  },
}
