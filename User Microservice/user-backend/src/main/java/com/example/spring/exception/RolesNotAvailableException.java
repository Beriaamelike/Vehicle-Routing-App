package com.example.spring.exception;

import java.util.List;

public class RolesNotAvailableException extends RuntimeException{
    public RolesNotAvailableException(List<String> roles){
        super("Roles Not Available: "+roles);
    }
}
