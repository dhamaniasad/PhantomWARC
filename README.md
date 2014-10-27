PhantomWARC
===========
#### Generate WARC files from dynamic webpages
____
##### Installation
```
Download archive from latest release: https://github.com/dhamaniasad/PhantomWARC/releases/latest & Unpack
pip install -r requirements.txt
```

##### Usage
```
import phantomwarc

phantomwarc.init_browser("http://www.google.com", ia=True)
```

##### Internet Archive Uploading
```
Get your Internet Archive S3-Like API Keys from: 
https://archive.org/account/s3.php
Set the Access Key and Secret Key as environment variables like so:
export IAS3_ACCESS_KEY=''
export IAS3_SECRET_KEY=''
```
