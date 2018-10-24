def traverse_match(data, key, value):

    if type(key) == STRING: 
        key_parts = key.split('.')
    else:
        # to account for recursion calls
        key_parts = key

    foreach i:kp in key_parts:
        if kp == '[]': # array to traverse 
            for d in data:
                match = traverse_match(d, key[i+1:], value)
                if match:
                    return True
        else: # object key
            data = data[kp]
    return data==value



                 
            
        

CREATE or REPLACE FUNCTION 
parse_key(key text) RETURNS JSON AS $$
$$ LANGUAGE plv8 IMMUTABLE STRICT;

CREATE or REPLACE FUNCTION 
traverse_match(data json, key text, value json) RETURNS TEXT AS $$

    var ret = data;
    var keys = key.split('.')
    var len = keys.length;
    
    for (var i=0; i<len; ++i) {
      if (ret != undefined) ret = ret[keys[i]];
    }    
   
  
    if (ret != undefined) {
      ret = ret.toString();
    }

    return ret;

$$ LANGUAGE plv8 IMMUTABLE STRICT;
