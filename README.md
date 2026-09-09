Thoroughly work in progress

insert your auth parameters into `env_template` for connecting to mariadb. Run init_database.py
to create and populate the initial database and tables.

Will add a systemd unit file soon to automate synchronizing the database with outputs from 
`/latest` api endpoint.

To do:
* Add indicators for all tracked items
* Infer how long to hold what volume of items, as well as when to buy and sell that volume
