#define NOMINMAX
#include <Windows.h>
#include <Mmdeviceapi.h>
#include <Functiondiscoverykeys_devpkey.h>
#include <Propvarutil.h>

#include <cstdio>
#include <string>

struct DeviceShareMode
{
    DWORD mode;
    BOOL isDefault;
};

struct IPolicyConfig : public IUnknown
{
    virtual HRESULT STDMETHODCALLTYPE GetMixFormat(PCWSTR, WAVEFORMATEX**) = 0;
    virtual HRESULT STDMETHODCALLTYPE GetDeviceFormat(PCWSTR, INT, WAVEFORMATEX**) = 0;
    virtual HRESULT STDMETHODCALLTYPE ResetDeviceFormat(PCWSTR) = 0;
    virtual HRESULT STDMETHODCALLTYPE SetDeviceFormat(PCWSTR, WAVEFORMATEX*, WAVEFORMATEX*) = 0;
    virtual HRESULT STDMETHODCALLTYPE GetProcessingPeriod(PCWSTR, INT, PINT64, PINT64) = 0;
    virtual HRESULT STDMETHODCALLTYPE SetProcessingPeriod(PCWSTR, PINT64) = 0;
    virtual HRESULT STDMETHODCALLTYPE GetShareMode(PCWSTR, DeviceShareMode*) = 0;
    virtual HRESULT STDMETHODCALLTYPE SetShareMode(PCWSTR, DeviceShareMode*) = 0;
    virtual HRESULT STDMETHODCALLTYPE GetPropertyValue(PCWSTR, const PROPERTYKEY&, PROPVARIANT*) = 0;
    virtual HRESULT STDMETHODCALLTYPE SetPropertyValue(PCWSTR, const PROPERTYKEY&, PROPVARIANT*) = 0;
    virtual HRESULT STDMETHODCALLTYPE SetDefaultEndpoint(PCWSTR, ERole) = 0;
    virtual HRESULT STDMETHODCALLTYPE SetEndpointVisibility(PCWSTR, INT) = 0;
};

static const CLSID CLSID_PolicyConfigClient =
{0x870af99c, 0x171d, 0x4f9e, {0xaf, 0x0d, 0xe6, 0x3d, 0xf4, 0x0c, 0x2b, 0xc9}};
static const IID IID_IPolicyConfig =
{0xf8679f50, 0x850a, 0x41cf, {0x9c, 0x72, 0x43, 0x0f, 0x29, 0x02, 0x90, 0xc8}};

template <typename T>
class ComPtr
{
public:
    ~ComPtr()
    {
        if (value_ != nullptr)
        {
            value_->Release();
        }
    }

    T** Put()
    {
        return &value_;
    }

    T* Get() const
    {
        return value_;
    }

    T* operator->() const
    {
        return value_;
    }

    void Reset()
    {
        if (value_ != nullptr)
        {
            value_->Release();
            value_ = nullptr;
        }
    }

private:
    T* value_ = nullptr;
};

std::wstring GetName(IMMDevice* device)
{
    ComPtr<IPropertyStore> store;
    if (FAILED(device->OpenPropertyStore(STGM_READ, store.Put())))
    {
        return L"";
    }
    PROPVARIANT value;
    PropVariantInit(&value);
    std::wstring name;
    if (SUCCEEDED(store->GetValue(PKEY_Device_FriendlyName, &value)) &&
        value.vt == VT_LPWSTR &&
        value.pwszVal != nullptr)
    {
        name = value.pwszVal;
    }
    PropVariantClear(&value);
    return name;
}

std::wstring GetId(IMMDevice* device)
{
    LPWSTR raw = nullptr;
    if (FAILED(device->GetId(&raw)) || raw == nullptr)
    {
        return L"";
    }
    std::wstring id = raw;
    CoTaskMemFree(raw);
    return id;
}

bool ContainsInsensitive(const std::wstring& text, const std::wstring& needle)
{
    if (needle.empty())
    {
        return true;
    }
    std::wstring left = text;
    std::wstring right = needle;
    CharLowerBuffW(left.data(), static_cast<DWORD>(left.size()));
    CharLowerBuffW(right.data(), static_cast<DWORD>(right.size()));
    return left.find(right) != std::wstring::npos;
}

int wmain(int argc, wchar_t** argv)
{
    const HRESULT init = CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED);
    if (FAILED(init))
    {
        return 2;
    }

    ComPtr<IMMDeviceEnumerator> enumerator;
    HRESULT hr = CoCreateInstance(
        __uuidof(MMDeviceEnumerator),
        nullptr,
        CLSCTX_ALL,
        IID_PPV_ARGS(enumerator.Put()));
    if (FAILED(hr))
    {
        CoUninitialize();
        return 3;
    }

    if (argc == 1 || std::wstring(argv[1]) == L"--list")
    {
        ComPtr<IMMDevice> defaultDevice;
        std::wstring defaultId;
        if (SUCCEEDED(enumerator->GetDefaultAudioEndpoint(eCapture, eConsole, defaultDevice.Put())))
        {
            defaultId = GetId(defaultDevice.Get());
        }

        ComPtr<IMMDeviceCollection> devices;
        hr = enumerator->EnumAudioEndpoints(eCapture, DEVICE_STATE_ACTIVE, devices.Put());
        if (FAILED(hr))
        {
            CoUninitialize();
            return 4;
        }

        UINT count = 0;
        devices->GetCount(&count);
        for (UINT index = 0; index < count; ++index)
        {
            ComPtr<IMMDevice> device;
            if (FAILED(devices->Item(index, device.Put())))
            {
                continue;
            }
            const std::wstring id = GetId(device.Get());
            const std::wstring name = GetName(device.Get());
            std::wprintf(
                L"default=%d\tname=%ls\tid=%ls\n",
                id == defaultId ? 1 : 0,
                name.c_str(),
                id.c_str());
        }
        CoUninitialize();
        return 0;
    }

    std::wstring targetId;
    if (std::wstring(argv[1]) == L"--set-id" && argc == 3)
    {
        targetId = argv[2];
    }
    else if (std::wstring(argv[1]) == L"--set-name" && argc == 3)
    {
        const std::wstring needle = argv[2];
        ComPtr<IMMDeviceCollection> devices;
        hr = enumerator->EnumAudioEndpoints(eCapture, DEVICE_STATE_ACTIVE, devices.Put());
        if (FAILED(hr))
        {
            CoUninitialize();
            return 5;
        }
        UINT count = 0;
        devices->GetCount(&count);
        for (UINT index = 0; index < count; ++index)
        {
            ComPtr<IMMDevice> device;
            if (SUCCEEDED(devices->Item(index, device.Put())) &&
                ContainsInsensitive(GetName(device.Get()), needle))
            {
                targetId = GetId(device.Get());
                break;
            }
        }
    }
    else
    {
        std::fwprintf(stderr, L"Use --list, --set-name SUBSTRING or --set-id ID.\n");
        CoUninitialize();
        return 6;
    }

    if (targetId.empty())
    {
        std::fwprintf(stderr, L"Capture endpoint not found.\n");
        CoUninitialize();
        return 7;
    }

    ComPtr<IPolicyConfig> policy;
    hr = CoCreateInstance(
        CLSID_PolicyConfigClient,
        nullptr,
        CLSCTX_ALL,
        IID_IPolicyConfig,
        reinterpret_cast<void**>(policy.Put()));
    if (FAILED(hr))
    {
        CoUninitialize();
        return 8;
    }

    hr = policy->SetDefaultEndpoint(targetId.c_str(), eConsole);
    if (FAILED(hr))
    {
        policy.Reset();
        enumerator.Reset();
        CoUninitialize();
        return 9;
    }
    std::wprintf(L"set_default_capture_id=%ls\n", targetId.c_str());
    policy.Reset();
    enumerator.Reset();
    CoUninitialize();
    return 0;
}
