-- Import the Prosody user manager module
local usermanager = require "core.usermanager";

-- Register a new user
usermanager.create_user(admin, simple, localhost);

-- Set any additional properties for the user if needed
-- usermanager.set_password(username, hostname, password);
