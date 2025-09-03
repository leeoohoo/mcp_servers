// JavaScript示例文件
function greetUser(name) {
    console.log(`Hello, ${name}!`);
    return `Welcome to our application, ${name}`;
}

class UserManager {
    constructor() {
        this.users = [];
    }
    
    addUser(user) {
        this.users.push(user);
    }
    
    getUsers() {
        return this.users;
    }
}

const manager = new UserManager();
manager.addUser({name: 'Alice', age: 30});
console.log(manager.getUsers());