package com.example.spring.service;

import com.example.spring.entity.Role;
import com.example.spring.repository.RoleRepository;
import lombok.AllArgsConstructor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

@Service
@AllArgsConstructor
public class RoleService {
    @Autowired
    private RoleRepository roleRepository;

    public void loadRoles(){
        List<Role> roles= new ArrayList<>();
        Role roleUser = new Role();
        roleUser.setRoleName("ROLE_USER");
        roles.add(roleUser);
        Role roleAdmin=new Role();
        roleAdmin.setRoleName("ROLE_ADMIN");
        roles.add(roleAdmin);
        roleRepository.saveAll(roles);

    }

}
