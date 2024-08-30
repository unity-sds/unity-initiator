locals {
  function_name = "${var.project}-${var.venue}-scheduled_task"
  tags = {
    Venue       = "dev"
    ServiceArea = "cs"
    Capability  = "trigger"
    CapVersion  = "0.0.1"
    Component   = "U-OD"
    Name        = "${var.project}-${var.venue}-cs-trigger-od"
    Proj        = var.project
    CreatedBy   = "cs"
    Env         = "dev"
    Stack       = "U-OD"
  }
}
