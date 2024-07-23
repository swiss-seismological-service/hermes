from hermes.utils.url import add_query_params


def test_add_query_params():
    url = 'http://www.google.com?name=John&age=30'
    params = {'name': 'Jane', 'age': 25, 'city': 'New York'}
    new_url = add_query_params(url, **params)

    assert new_url == 'http://www.google.com?name=Jane&age=25&city=New+York'
