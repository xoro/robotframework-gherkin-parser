*** Keywords ***
before_test
    [Tags]    hook:before-test
    [Arguments]    ${context}=    ${test}=
    Log    before test
    # Fail    har har test

before_suite
    [Tags]    hook:before-suite
    [Arguments]    ${context}=    ${suite}=
    Log    hook before suite

before_keyword
    [Tags]    hook:before-keyword
    [Arguments]    ${context}=    ${suite}=
    Log    before keyword
    Fail    blah
    RETURN    after_keyword

after_keyword
    [Tags]    hook:after-step
    [Arguments]    ${context}=    ${suite}=
    Log    after step

before_tag
    [Tags]    hook:before-tag
    [Arguments]    ${context}=    ${suite}=
    Log    before suite

start_browser
    [Tags]    hook:before-tag:browser
    [Arguments]    ${context}=    ${suite}=
    Log    before suite
