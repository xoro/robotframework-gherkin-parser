*** Settings ***
Resource            ./steps/hooks.resource

Suite Setup         Log    Suite Setup
Suite Teardown      Log    Suite Teardown
Test Setup          Log    Test Setup
Test Teardown       Log    Test Teardown
