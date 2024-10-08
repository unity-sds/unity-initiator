locals {
  log_group_name = "${var.project}-${var.venue}-initiator-centralized-log-group"
  tags = {
    Venue       = "dev"
    ServiceArea = "cs"
    Capability  = "initiator"
    CapVersion  = "0.0.1"
    Component   = "U-OD"
    Name        = "${var.project}-${var.venue}-cs-initiator-od"
    Proj        = var.project
    CreatedBy   = "cs"
    Env         = "dev"
    Stack       = "U-OD"
  }
}
