"""Quick test for the deprecated Azure image reference auto-correction."""

from app.services.azure_validator import AzureTerraformValidator


def test_fix_deprecated_ubuntu_server():
    """Test that UbuntuServer/22.04-LTS is auto-corrected."""
    tf_code = '''
resource "azurerm_linux_virtual_machine" "web_vm_01" {
  name                = "web-vm-01"
  location            = "eastus"
  resource_group_name = azurerm_resource_group.rg.name
  size                = "Standard_D2s_v3"

  source_image_reference {
    publisher = "Canonical"
    offer     = "UbuntuServer"
    sku       = "22.04-LTS"
    version   = "latest"
  }
}
'''
    result, issues = AzureTerraformValidator.validate_and_fix_main_tf(tf_code)

    print("=" * 60)
    print("TEST 1: UbuntuServer/22.04-LTS -> 0001-com-ubuntu-server-jammy/22_04-lts")
    print("=" * 60)
    print("Issues fixed:", issues)
    print()
    print("Generated code:")
    print(result)

    assert '0001-com-ubuntu-server-jammy' in result, "Offer was not corrected!"
    assert '22_04-lts' in result, "SKU was not corrected!"
    assert 'UbuntuServer' not in result, "Old offer still present!"
    print("✅ PASSED\n")


def test_fix_deprecated_ubuntu_18():
    """Test that UbuntuServer/18.04-LTS is auto-corrected."""
    tf_code = '''
  source_image_reference {
    publisher = "Canonical"
    offer     = "UbuntuServer"
    sku       = "18.04-LTS"
    version   = "latest"
  }
'''
    result, issues = AzureTerraformValidator._fix_deprecated_image_references(tf_code)

    print("=" * 60)
    print("TEST 2: UbuntuServer/18.04-LTS -> 0001-com-ubuntu-server-bionic/18_04-lts-gen2")
    print("=" * 60)
    print("Issues fixed:", issues)
    print("Generated code:")
    print(result)

    assert '0001-com-ubuntu-server-bionic' in result, "Offer was not corrected!"
    assert '18_04-lts-gen2' in result, "SKU was not corrected!"
    print("✅ PASSED\n")


def test_correct_image_not_modified():
    """Test that already-correct image references are NOT touched."""
    tf_code = '''
  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts"
    version   = "latest"
  }
'''
    result, issues = AzureTerraformValidator._fix_deprecated_image_references(tf_code)

    print("=" * 60)
    print("TEST 3: Correct image should NOT be modified")
    print("=" * 60)
    print("Issues fixed:", issues)

    assert len(issues) == 0, f"Unexpected issues: {issues}"
    assert result == tf_code, "Content was modified when it shouldn't be!"
    print("✅ PASSED\n")


if __name__ == "__main__":
    test_fix_deprecated_ubuntu_server()
    test_fix_deprecated_ubuntu_18()
    test_correct_image_not_modified()
    print("🎉 All tests passed!")
