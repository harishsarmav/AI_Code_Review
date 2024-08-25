// example.cpp
#include <iostream>
using namespace std;

int main() {
    int* ptr = new int(5);
    cout << "Value: " << *ptr << endl;
    delete ptr; // Proper memory management, but let's check with the AI review tool
    return 0;
}
