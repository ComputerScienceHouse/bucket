from json import dumps
from flask import flash, Flask, redirect, render_template, request
from os import environ
from flask_pyoidc.provider_configuration import *
from flask_pyoidc.flask_pyoidc import OIDCAuthentication
from boto3 import client
from botocore.exceptions import ClientError

_policy = dumps({
    'Version': '2012-10-17',
    'Statement': [{
        'Action': ['s3:GetObject'],
        'Effect': 'Allow',
        'Principal': '*',
        'Resource': 'arn:aws:s3:::!/*',
        'Sid': 'Public'
    }]
})

app = Flask(__name__)
app.config.update(
    PREFERRED_URL_SCHEME = environ.get('URL_SCHEME', 'https'),
    SECRET_KEY = environ['SECRET_KEY'], SERVER_NAME = environ['SERVER_NAME']
)
app.config['SECRET_KEY'] = environ['SECRET_KEY']
app.jinja_env.lstrip_blocks = True
app.jinja_env.trim_blocks = True
app.url_map.strict_slashes = False

_config = ProviderConfiguration(
    environ['OIDC_ISSUER'], client_metadata = ClientMetadata(
        environ['OIDC_CLIENT_ID'], environ['OIDC_CLIENT_SECRET']
    )
)
_auth = OIDCAuthentication({'default': _config}, app)

@app.route('/change', methods = ['POST'])
@_auth.oidc_auth('default')
def change():
    if 'access_key' not in request.form:
        flash('No access key provided.')
        return redirect('/')
    elif 'secret_key' not in request.form:
        flash('No secret key provided.')
        return redirect('/')
    elif 'bucket' not in request.form:
        flash('No bucket provided.')
        return redirect('/')
    s3 = client(
        's3', aws_access_key_id = request.form['access_key'],
        aws_secret_access_key = request.form['secret_key'],
        endpoint_url = environ['S3_ENDPOINT']
    )
    try:
        s3.head_bucket(Bucket = request.form['bucket'])
    except:
        try:
            s3.create_bucket(Bucket = request.form['bucket'])
        except ClientError as error:
            flash(error.response['Error']['Code'])
            return redirect('/')
    policy = request.form.get('policy', 'None')
    if policy == 'None':
        try:
            s3.delete_bucket_policy(Bucket = request.form['bucket'])
            flash('Successfully cleared policy.')
        except ClientError as error:
            flash(error.response['Error']['Code'])
    else:
        try:
            s3.put_bucket_policy(
                Bucket = request.form['bucket'],
                Policy = _policy.replace('!', request.form['bucket'])
            )
            flash('Successfully set policy.')
        except ClientError as error:
            flash(error.response['Error']['Code'])
    return redirect('/')

@app.route('/')
@_auth.oidc_auth('default')
def index():
    return render_template('index.html')
