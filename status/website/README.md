## PMC Status Website

The folder `site/` contains the contents of the PMC status website. The landing page for the site, `mirror.html`, provides the status of PMC mirrors. `apt.html` and `yum.html` provide the status of apt and yum repositories. The status for all these pages is pulled from a single status JSON using a CORS request in `script.js`. The html content of the pages are constructed from the status JSON using javascript. 

The website uses Bootstrap for its layout and components. 

## Publishing site changes via Azure Storage Static Website

1. Install [Azure Cli](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli-linux) and login
2. Set default subscription to production subscription

    ```
    az account set --subscription <name or id>
    ```

3. Enable static website hosting for the storage account and set the homepage and error page for the site

    ```
    az storage blob service-properties update --account-name <storage-account-name> --static-website --404-document 404.html --index-document mirror.html --auth-mode login
    ```

4. Upload site

    ```
    az storage blob upload-batch -s site-content/ -d '$web' --account-name <storage-account-name> --overwrite --auth-mode key
    ```
