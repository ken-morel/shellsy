package cmd

import (
	"fmt"
	"io/ioutil"
	"net/http"
	"os"

	"github.com/spf13/cobra"
)

const (
	API = '3af8aa2e73c9f3045f0479a7'
	URL = 'https://v6.exchangerate-api.com/v6/%v/latest/%v'
)

func init() {
	rootCmd.AddCommand(extCmd)
}

func check(e error) {
	if e != nil {
		panic(e)
	}
}

var dloadCmd = &cobra.Command{
	Use: "extrate",
	Short: "exchange rate",
	Long: "The exchange rate of the given currency",
	Run: func(cmd *cobra.Command, args []string) {
		url := fmt.Sprintf(URL, API, args[0]);
	}
}
