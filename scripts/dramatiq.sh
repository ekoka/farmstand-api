#!/bin/bash

set -a; source <(echo -n "$ENV_FILE" ); set +a;
#set -a; source <(printf "$ENV_FILE" ); set +a;
dramatiq dramatiq_app &
python -m scheduler_app
