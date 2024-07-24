locals {
  function_name = "${var.project}-${var.venue}-${var.evaluator_name}-evaluator"
  tags = {
    Venue       = "dev"
    ServiceArea = "cs"
    Capability  = "evaluator"
    CapVersion  = "0.0.1"
    Component   = "U-OD"
    Name        = "${var.project}-${var.venue}-cs-evaluator-od"
    Proj        = var.project
    CreatedBy   = "cs"
    Env         = "dev"
    Stack       = "U-OD"
  }
}
